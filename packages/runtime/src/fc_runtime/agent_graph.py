"""P3.2 — LangGraph 风格控制图

核心概念（符合方法论的有向图模型）：
  - Node: 每个 Agent 作为一个计算节点
  - Edge: 节点之间的固定顺序边
  - Conditional Edge: 根据节点输出选择下一个节点
  - State: 所有节点共享的可变状态对象
  - Entry/Finish: 开始/结束节点
  - Cycle: 支持有限次数的重试循环

使用示例：
    g = AgentGraph()
    g.add_node("requirement", _requirement_node)
    g.add_node("design", _design_node)
    g.add_node("modeling", _modeling_node)
    g.add_node("review", _review_node)
    g.add_node("drafting", _drafting_node)
    g.add_node("annotation", _annotation_node)
    g.set_entry_point("requirement")
    g.add_conditional_edges("review", _review_router, {
        "pass": "drafting",
        "retry_design": "design",  # DESGIN 级回滚
        "retry_modeling": "modeling",  # CODE 级回滚
        "fail": END,
    })
    g.add_edge("annotation", END)

    result = g.run(user_input="一个盒子 100x50x25mm",
                    max_steps=20)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol

from fc_runtime.agent_logging import AgentLogger, get_logger
from fc_runtime.agent_schemas import (
    CADModelingOutput,
    DrawingOutput,
    GeometryReviewReport,
    ModelingPlan,
    RequirementDocument,
    AnnotationReviewReport,
)


# ── 常量 ───────────────────────────────────

END = "__end__"


class NodeStatus(str, Enum):
    """节点执行状态。"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ── 共享 State ────────────────────────────

@dataclass
class GraphState:
    """节点间共享的可变状态。

    类似 LangGraph 的 StateGraph：每个节点读写同一个 dict-like
    的状态对象，节点之间通过共享状态通信。
    """
    user_input: str = ""
    requirement: RequirementDocument | None = None
    plan: ModelingPlan | None = None
    model_output: CADModelingOutput | None = None
    geometry_review: GeometryReviewReport | None = None
    drawing_output: DrawingOutput | None = None
    annotation_review: AnnotationReviewReport | None = None
    errors: list[tuple[str, str]] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    attempts: dict[str, int] = field(default_factory=dict)  # node -> 执行次数
    finished: bool = False
    elapsed_sec: float = 0.0

    def mark_attempt(self, node: str) -> int:
        self.attempts[node] = self.attempts.get(node, 0) + 1
        return self.attempts[node]

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_input": self.user_input,
            "requirement": (
                self.requirement.model_dump(mode="json")
                if self.requirement else None
            ),
            "plan": self.plan.model_dump(mode="json") if self.plan else None,
            "model_output": (
                self.model_output.model_dump(mode="json")
                if self.model_output else None
            ),
            "geometry_review": (
                self.geometry_review.model_dump(mode="json")
                if self.geometry_review else None
            ),
            "drawing_output": (
                self.drawing_output.model_dump(mode="json")
                if self.drawing_output else None
            ),
            "annotation_review": (
                self.annotation_review.model_dump(mode="json")
                if self.annotation_review else None
            ),
            "errors": self.errors,
            "trace": self.trace,
            "attempts": self.attempts,
            "finished": self.finished,
            "elapsed_sec": round(self.elapsed_sec, 3),
        }


# ── Node Protocol ─────────────────────────

class NodeFn(Protocol):
    """节点函数签名：接收 GraphState，返回可选的下一个节点名。"""

    def __call__(self, state: GraphState) -> str | None: ...


@dataclass
class Node:
    name: str
    fn: NodeFn
    max_attempts: int = 3


@dataclass
class ConditionalEdge:
    """条件边：从 source 出发，通过 router(state) -> next_node。"""
    source: str
    router: Callable[[GraphState], str]
    mapping: dict[str, str]  # router 输出 -> 下一个节点名


# ── Graph Orchestrator ─────────────────────

class AgentGraph:
    """LangGraph 风格的 Agent 控制图。

    典型拓扑：
      requirement -> design -> modeling -> review ---+
                             ^          |              |
                             |       FAIL 回滚         v
                          (CODE)                     drafting
                             ^                       |
                          (DESIGN)                    v
                         design <--------------- annotation -> END
    """

    def __init__(self, verbose: bool = False) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: list[tuple[str, str]] = []  # from -> to
        self._cond_edges: list[ConditionalEdge] = []
        self._entry_point: str | None = None
        self._log: AgentLogger = get_logger("agent_graph", verbose=verbose)

    # ── 构建 API ──────────────────────

    def add_node(self, name: str, fn: NodeFn,
                  max_attempts: int = 3) -> None:
        self._nodes[name] = Node(name=name, fn=fn, max_attempts=max_attempts)

    def add_edge(self, from_node: str, to_node: str) -> None:
        self._edges.append((from_node, to_node))

    def add_conditional_edges(
        self,
        source: str,
        router: Callable[[GraphState], str],
        mapping: dict[str, str],
    ) -> None:
        self._cond_edges.append(ConditionalEdge(
            source=source,
            router=router,
            mapping=mapping,
        ))

    def set_entry_point(self, node: str) -> None:
        self._entry_point = node

    # ── 运行 API ───────────────────────

    def run(self, user_input: str, max_steps: int = 30,
            max_total_seconds: int = 600) -> GraphState:
        """执行图 — 从 entry_point 开始，沿着边流动，直到 END。"""
        if self._entry_point is None:
            raise RuntimeError("AgentGraph: 必须先调用 set_entry_point()")

        start = time.time()
        state = GraphState(user_input=user_input)
        current = self._entry_point
        steps = 0

        self._log.stage_enter("graph_run", input=user_input[:80])

        while current != END and steps < max_steps:
            elapsed = time.time() - start
            if elapsed > max_total_seconds:
                state.errors.append(
                    ("CODE", f"Graph 超时：超过 {max_total_seconds}s")
                )
                state.trace.append({
                    "step": steps, "node": current,
                    "status": NodeStatus.FAILED.value,
                    "reason": "timeout",
                })
                self._log.stage_exit("graph_run", success=False,
                                      reason="timeout")
                state.finished = True
                state.elapsed_sec = time.time() - start
                return state

            if current not in self._nodes:
                state.errors.append(
                    ("CODE", f"Unknown node: {current}")
                )
                break

            node_obj = self._nodes[current]
            attempts = state.mark_attempt(current)

            # 防止单个节点无限循环
            if attempts > node_obj.max_attempts:
                state.errors.append(
                    ("CODE", f"节点 {current} 超过最大重试次数 "
                             f"({node_obj.max_attempts})")
                )
                state.trace.append({
                    "step": steps, "node": current,
                    "status": NodeStatus.FAILED.value,
                    "reason": "max_attempts_exceeded",
                })
                break

            self._log.task("node", "run", node=current, attempt=attempts)
            node_start = time.time()

            try:
                with self._log.measure_stage(current):
                    result_hint = node_obj.fn(state)
            except Exception as exc:
                node_elapsed = time.time() - node_start
                state.trace.append({
                    "step": steps, "node": current,
                    "status": NodeStatus.FAILED.value,
                    "elapsed_sec": round(node_elapsed, 3),
                    "error": str(exc),
                })
                state.errors.append(("CODE", f"{current}: {exc}"))
                self._log.error("CODE", f"{current}: {exc}")
                break

            node_elapsed = time.time() - node_start
            state.trace.append({
                "step": steps, "node": current,
                "status": NodeStatus.SUCCESS.value,
                "elapsed_sec": round(node_elapsed, 3),
            })

            # 决定下一个节点
            next_node = self._route(current, state, result_hint)
            current = next_node
            steps += 1

        if current == END:
            state.trace.append({"step": steps, "node": END,
                                 "status": "finished"})
            self._log.stage_exit("graph_run", success=True, steps=steps)
        elif steps >= max_steps:
            state.errors.append(("CODE", f"图执行超过 {max_steps} 步"))
            self._log.stage_exit("graph_run", success=False, reason="max_steps")

        state.finished = True
        state.elapsed_sec = time.time() - start
        return state

    # ── 路由 ───────────────────────────

    def _route(self, current: str, state: GraphState,
               hint: str | None) -> str:
        # 1) 优先：条件边（router 输出）
        for ce in self._cond_edges:
            if ce.source == current:
                key = ce.router(state) if hint is None else hint
                # 如果 hint 与 router 不同，以 hint 为准
                if hint is not None and hint in ce.mapping:
                    return ce.mapping[hint]
                if key in ce.mapping:
                    return ce.mapping[key]
                # router 返回的键不在 mapping 中 → 默认走第一个
                if ce.mapping:
                    return next(iter(ce.mapping.values()))

        # 2) 普通边：from -> to（按顺序取第一条匹配）
        for src, dst in self._edges:
            if src == current:
                return dst

        # 3) 无路可走 → END
        return END

    # ── 调试/诊断 ───────────────────────

    def describe(self) -> str:
        """返回图结构的人类可读描述。"""
        lines = ["== AgentGraph Structure =="]
        lines.append(f"Entry: {self._entry_point}")
        lines.append(f"Nodes: {sorted(self._nodes.keys())}")
        if self._edges:
            lines.append("Edges:")
            for a, b in self._edges:
                lines.append(f"  {a} -> {b}")
        if self._cond_edges:
            lines.append("Conditional Edges:")
            for ce in self._cond_edges:
                keys = ", ".join(ce.mapping.keys())
                lines.append(f"  {ce.source} -> ?  [{keys}]")
        return "\n".join(lines)


# ── 内置：标准六节点图 ─────────────────────

def build_standard_graph(
    max_modeling_retries: int = 3,
    max_design_retries: int = 2,
    verbose: bool = False,
) -> AgentGraph:
    """构建方法论要求的标准六节点控制图。

    Nodes:
      requirement ── 需求解析
      design      ── 设计规划
      modeling    ── CAD建模
      review      ── 几何审查（含条件分支）
      drafting    ── 出图
      annotation  ── 标注合规
    """
    from fc_runtime.agent_schemas import ErrorLevel, Verdict
    from fc_runtime.annotation_agent import AnnotationComplianceAgent
    from fc_runtime.design_agent import DesignAgent
    from fc_runtime.drafting_agent import DraftingAgent
    from fc_runtime.geometry_review_agent import GeometryReviewAgent
    from fc_runtime.modeling_agent import CADModelingAgent
    from fc_runtime.requirement_agent import RequirementAgent

    req_agent = RequirementAgent()
    design_agent = DesignAgent()
    modeling_agent = CADModelingAgent()
    review_agent = GeometryReviewAgent()
    drafting_agent = DraftingAgent()
    annotation_agent = AnnotationComplianceAgent()

    g = AgentGraph(verbose=verbose)

    # ── 节点定义 ─────────────────────

    def _requirement_node(state: GraphState) -> str:
        state.requirement = req_agent.parse(state.user_input)
        return "pass"

    def _design_node(state: GraphState) -> str:
        if state.requirement is None:
            raise RuntimeError("design: state.requirement is None")
        state.plan = design_agent.plan(state.requirement)
        return "pass"

    def _modeling_node(state: GraphState) -> str:
        if state.plan is None or state.requirement is None:
            raise RuntimeError("modeling: plan/requirement is None")
        state.model_output = modeling_agent.execute_plan(
            state.plan, state.requirement, f"model_{int(time.time())}"
        )
        return "pass"

    def _review_node(state: GraphState) -> str:
        if state.model_output is None:
            raise RuntimeError("review: model_output is None")
        report = review_agent.review(state.model_output, state.requirement)
        state.geometry_review = report
        if report.verdict == Verdict.PASS:
            return "pass"
        lvl = report.error_level
        if lvl == ErrorLevel.DESIGN:
            return "retry_design"
        return "retry_modeling"

    def _drafting_node(state: GraphState) -> str:
        if state.requirement is None:
            raise RuntimeError("drafting: requirement is None")
        state.drawing_output = drafting_agent.execute(
            state.requirement, "drawing_default"
        )
        return "pass"

    def _annotation_node(state: GraphState) -> str:
        if state.drawing_output is None or state.requirement is None:
            raise RuntimeError("annotation: missing inputs")
        state.annotation_review = annotation_agent.review(
            state.drawing_output, state.requirement
        )
        return "pass"

    g.add_node("requirement", _requirement_node, max_attempts=1)
    g.add_node("design", _design_node, max_attempts=max_design_retries)
    g.add_node("modeling", _modeling_node, max_attempts=max_modeling_retries)
    g.add_node("review", _review_node, max_attempts=1)
    g.add_node("drafting", _drafting_node, max_attempts=3)
    g.add_node("annotation", _annotation_node, max_attempts=1)

    g.set_entry_point("requirement")

    # ── 普通边 ───────────────────────
    g.add_edge("requirement", "design")
    g.add_edge("design", "modeling")
    g.add_edge("modeling", "review")
    g.add_edge("drafting", "annotation")

    # ── 条件边：review 决定回滚或前进 ──
    g.add_conditional_edges(
        "review",
        _review_node,  # 使用节点函数返回作为路由键
        mapping={
            "pass": "drafting",
            "retry_design": "design",
            "retry_modeling": "modeling",
        },
    )
    g.add_conditional_edges(
        "annotation",
        lambda state: (
            "pass"
            if (state.annotation_review
                and state.annotation_review.verdict == Verdict.PASS)
            else "retry_drafting"
        ),
        mapping={
            "pass": END,
            "retry_drafting": "drafting",
        },
    )

    return g
