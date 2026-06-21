"""P3.3 — 知识库 / 经验库 + 反馈回路

核心设计：
  Experience 条目：一次完整的流水线执行（成功或失败）的摘要
    - 任务描述（part_type, dimensions）
    - 使用了哪些特征步骤
    - 几何审查结果（通过/失败 + 失败项）
    - 标注合规结果
    - 总体耗时
    - 成功或失败 + 失败原因（如有）
    - 人工标注的"最佳实践"标签（expert_hint）

  ExperienceLibrary:
    - 持久化到 JSONL 文件（一行一个 Experience）
    - 按关键词搜索 / 按零件类型搜索
    - 计算零件类型的平均成功率
    - 提取"最佳实践"（success=True 且耗时最短的 K 个）

  FeedbackLoop:
    - 将当前执行结果写入知识库
    - 在新任务启动时，自动推荐最相关的历史经验
    - 辅助设计规划 Agent（向其注入经验建议）

使用示例：
    lib = ExperienceLibrary("experience.jsonl")
    lib.record(state, success=True, expert_hint="长轴件优先车削")
    advice = lib.recommend("bolt_m6x30")  # 返回相关历史经验
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from fc_runtime.agent_graph import GraphState
from fc_runtime.agent_logging import AgentLogger, get_logger


# ── Experience 数据结构 ─────────────────

@dataclass
class Experience:
    """一次完整流水线执行的可总结经验。"""
    id: str
    timestamp: float
    part_type: str
    dimensions: dict[str, float]
    material: str
    tolerance_grade: str
    success: bool
    total_elapsed_sec: float
    feature_steps: list[str]
    geometry_checks: list[dict[str, Any]]
    annotation_checks: list[dict[str, Any]]
    errors: list[tuple[str, str]]
    attempts: dict[str, int]
    expert_hint: str = ""  # 可由人工事后补充的最佳实践提示
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "part_type": self.part_type,
            "dimensions": self.dimensions,
            "material": self.material,
            "tolerance_grade": self.tolerance_grade,
            "success": self.success,
            "total_elapsed_sec": self.total_elapsed_sec,
            "feature_steps": self.feature_steps,
            "geometry_checks": self.geometry_checks,
            "annotation_checks": self.annotation_checks,
            "errors": self.errors,
            "attempts": self.attempts,
            "expert_hint": self.expert_hint,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Experience":
        return cls(
            id=data.get("id", ""),
            timestamp=float(data.get("timestamp", time.time())),
            part_type=str(data.get("part_type", "unknown")),
            dimensions=dict(data.get("dimensions", {})),
            material=str(data.get("material", "")),
            tolerance_grade=str(data.get("tolerance_grade", "")),
            success=bool(data.get("success", False)),
            total_elapsed_sec=float(data.get("total_elapsed_sec", 0.0)),
            feature_steps=list(data.get("feature_steps", [])),
            geometry_checks=list(data.get("geometry_checks", [])),
            annotation_checks=list(data.get("annotation_checks", [])),
            errors=[tuple(e) if isinstance(e, (list, tuple)) else ("CODE", str(e))
                     for e in data.get("errors", [])],
            attempts=dict(data.get("attempts", {})),
            expert_hint=str(data.get("expert_hint", "")),
            tags=list(data.get("tags", [])),
        )


# ── Experience Library ─────────────────

class ExperienceLibrary:
    """基于文件的经验库（JSONL 存储，可追加）。"""

    def __init__(self, path: str = "fc_experience.jsonl",
                  verbose: bool = False) -> None:
        self._path = Path(path)
        self._log: AgentLogger = get_logger("experience_library",
                                             verbose=verbose)
        if not self._path.parent.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)

    # ── 写 API ────────────────────────

    def record_from_state(
        self,
        state: GraphState,
        success: bool,
        expert_hint: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """将一次图执行结果保存为一条 Experience。"""
        exp_id = f"exp_{int(time.time() * 1000)}"
        requirement = state.requirement

        feature_steps: list[str] = []
        if state.plan is not None:
            try:
                feature_steps = [
                    (f"{fs.operation.value if hasattr(fs, 'operation') else str(fs)}"
                      f"({'|'.join(f'{k}={v}' for k, v in fs.parameters.items())})")
                    if hasattr(state.plan, "features") and state.plan.features
                    else ""
                    for fs in state.plan.features
                ]
                feature_steps = [s for s in feature_steps if s]
            except Exception:
                feature_steps = []

        geo_checks: list[dict[str, Any]] = []
        if state.geometry_review is not None:
            try:
                geo_checks = [
                    {"name": c.check_name, "passed": c.passed,
                      "detail": c.detail}
                    for c in state.geometry_review.checks
                ]
            except Exception:
                geo_checks = []

        ann_checks: list[dict[str, Any]] = []
        if state.annotation_review is not None:
            try:
                ann_checks = [
                    {"name": c.check_name, "passed": c.passed,
                      "detail": c.detail}
                    for c in state.annotation_review.checks
                ]
            except Exception:
                ann_checks = []

        exp = Experience(
            id=exp_id,
            timestamp=time.time(),
            part_type=(requirement.part_type.value
                       if requirement and requirement.part_type else "unknown"),
            dimensions=dict(requirement.dimensions) if requirement else {},
            material=(requirement.material or "") if requirement else "",
            tolerance_grade=(requirement.tolerance_grade.value
                               if requirement and requirement.tolerance_grade
                               else ""),
            success=success,
            total_elapsed_sec=state.elapsed_sec,
            feature_steps=feature_steps,
            geometry_checks=geo_checks,
            annotation_checks=ann_checks,
            errors=list(state.errors),
            attempts=dict(state.attempts),
            expert_hint=expert_hint,
            tags=list(tags) if tags else [],
        )

        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(exp.to_dict(), ensure_ascii=False) + "\n")

        self._log.task("library", "recorded", id=exp_id,
                       success=success, part=exp.part_type)
        return exp_id

    def record(
        self,
        experience: Experience,
    ) -> str:
        """保存一个手工构建的 Experience 对象。"""
        if not experience.id:
            experience.id = f"exp_{int(time.time() * 1000)}"
        if not experience.timestamp:
            experience.timestamp = time.time()

        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(experience.to_dict(), ensure_ascii=False) + "\n")
        return experience.id

    # ── 读 API ────────────────────────

    def count(self) -> int:
        if not self._path.exists():
            return 0
        with open(self._path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)

    def iter_experiences(self) -> list[Experience]:
        if not self._path.exists():
            return []
        result: list[Experience] = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    result.append(Experience.from_dict(data))
                except json.JSONDecodeError:
                    continue
        return result

    # ── 查询 / 分析 ────────────────────

    def recommend(
        self,
        part_type: str,
        material: str | None = None,
        top_k: int = 3,
    ) -> list[Experience]:
        """根据零件类型 + 材料推荐相关历史经验（只看成功的）。"""
        exps = self.iter_experiences()
        candidates = [e for e in exps if e.success]
        if part_type:
            candidates = [e for e in candidates
                          if e.part_type == part_type or part_type in e.part_type]
        if material:
            candidates = [e for e in candidates if material.lower() in e.material.lower()]

        # 按耗时排序（越短越好），取 top_k
        candidates.sort(key=lambda e: e.total_elapsed_sec)
        return candidates[:top_k]

    def success_rate(self, part_type: str) -> float:
        """计算指定零件类型的历史成功率。"""
        exps = self.iter_experiences()
        matched = [e for e in exps if e.part_type == part_type]
        if not matched:
            return 0.0
        return sum(1 for e in matched if e.success) / len(matched)

    def common_failures(
        self,
        part_type: str | None = None,
        limit: int = 5,
    ) -> list[tuple[str, int]]:
        """返回常见失败原因（按出现频次排序）。"""
        exps = self.iter_experiences()
        failed = [e for e in exps if not e.success]
        if part_type:
            failed = [e for e in failed if e.part_type == part_type]

        from collections import Counter
        reasons: Counter[str] = Counter()
        for e in failed:
            if e.errors:
                for _, msg in e.errors:
                    reasons[msg[:60]] += 1
            else:
                reasons["unknown"] += 1
        return reasons.most_common(limit)

    def expert_hints(self, part_type: str) -> list[str]:
        """提取指定零件类型的所有专家提示（expert_hint）。"""
        exps = self.iter_experiences()
        return [e.expert_hint for e in exps
                if e.expert_hint and e.part_type == part_type]

    # ── 维护 API ──────────────────────

    def add_expert_hint(self, experience_id: str, hint: str) -> bool:
        """给已有经验补充专家提示（覆写整个文件）。"""
        if not self._path.exists():
            return False
        exps = self.iter_experiences()
        found = False
        for e in exps:
            if e.id == experience_id:
                e.expert_hint = hint
                found = True
        if not found:
            return False
        with open(self._path, "w", encoding="utf-8") as f:
            for e in exps:
                f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")
        return True

    def clear(self) -> None:
        """清空经验库。"""
        if self._path.exists():
            self._path.unlink()
        self._log.task("library", "cleared")


# ── FeedbackLoop ──────────────────────────

class FeedbackLoop:
    """将经验库与 AgentGraph 绑定：启动前推荐经验、结束后保存经验。"""

    def __init__(self, library: ExperienceLibrary) -> None:
        self._lib = library
        self._log: AgentLogger = get_logger("feedback_loop")

    def pre_run(self, user_input: str) -> list[str]:
        """在图启动前：基于 keywords 提取 part_type → 返回建议列表。"""
        # 尝试从 user_input 中提取关键字
        keywords = [
            ("box", ["box", "cube", "盒子", "方块"]),
            ("shaft", ["shaft", "轴", "轴件"]),
            ("bolt", ["bolt", "螺丝", "螺栓"]),
            ("cylinder", ["cylinder", "圆柱", "柱"]),
            ("gear", ["gear", "齿轮"]),
            ("flange", ["flange", "法兰"]),
        ]
        matched: list[str] = []
        lower = user_input.lower()
        for pt, words in keywords:
            if any(w in lower for w in words):
                matched.append(pt)

        suggestions: list[str] = []
        for pt in matched:
            exps = self._lib.recommend(pt, top_k=2)
            for e in exps:
                if e.expert_hint:
                    suggestions.append(f"[{pt}] 专家提示: {e.expert_hint}")
                else:
                    suggestions.append(
                        f"[{pt}] 历史最佳: 特征数={len(e.feature_steps)}, "
                        f"耗时={e.total_elapsed_sec:.1f}s"
                    )

        if suggestions:
            self._log.task("feedback", "recommend", count=len(suggestions))
        return suggestions

    def post_run(self, state: GraphState, success: bool,
                  expert_hint: str = "") -> str:
        """在图结束后：将结果保存为经验。"""
        return self._lib.record_from_state(
            state, success=success, expert_hint=expert_hint
        )
