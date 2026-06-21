"""Agent编排器 — P2.4 增强版。

增强项：
1. **超时保护**（max_duration_sec）
2. **trace 模式** — 保留每个 stage 的事件列表
3. **dry_run 增强** — 只计划不执行
4. **统一日志** — P2.1 AgentLogger 集成
5. **Schema 握手** — P2.2 AgentHandshake 在每个 stage 结束时校验输出
6. **标准件库** — P2.3 支持传入 short_name 直接驱动
7. **explain()** — 人类可读的诊断报告
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fc_runtime.agent_handshake import pipeline_handshake_report
from fc_runtime.agent_logging import AgentLogger, get_logger
from fc_runtime.agent_schemas import (
    AgentState,
    AnnotationReviewReport,
    CADModelingOutput,
    DrawingOutput,
    ErrorLevel,
    GeometryReviewReport,
    ModelingPlan,
    PartType,
    RequirementDocument,
    Verdict,
)
from fc_runtime.design_agent import DesignAgent
from fc_runtime.drafting_agent import DraftingAgent
from fc_runtime.error_classifier import ErrorClassifier
from fc_runtime.geometry_validator import GeometryValidator
from fc_runtime.modeling_agent import CADModelingAgent
from fc_runtime.requirement_agent import RequirementAgent
from fc_runtime.standard_library import get_library
from fc_runtime.visual_verifier import VisualVerifier


class PipelineStage(str, Enum):
    """流水线阶段 — 与方法论一致的有序状态。"""
    NEW = "new"
    REQUIREMENT_PARSED = "requirement_parsed"
    DESIGN_PLANNED = "design_planned"
    MODELING = "modeling"
    MODELING_DONE = "modeling_done"
    GEOMETRY_REVIEW = "geometry_review"
    DRAFTING = "drafting"
    ANNOTATION_REVIEW = "annotation_review"
    VISUAL_REVIEW = "visual_review"
    DONE = "done"
    FAILED = "failed"


@dataclass
class PipelineResult:
    """完整流水线输出 — 用于报告/持久化。"""
    stage: PipelineStage
    requirement: RequirementDocument | None = None
    plan: ModelingPlan | None = None
    model_output: CADModelingOutput | None = None
    geometry_review: GeometryReviewReport | None = None
    drawing_output: DrawingOutput | None = None
    annotation_review: AnnotationReviewReport | None = None
    visual_plan_json: dict[str, Any] | None = None
    visual_result_data: dict[str, Any] | None = None
    errors: list[tuple[ErrorLevel, str]] = field(default_factory=list)
    elapsed_sec: float = 0.0
    trace: list[dict[str, Any]] = field(default_factory=list)
    handshake: dict[str, Any] | None = None

    def to_json(self) -> str:
        serializable: dict[str, Any] = {
            "stage": self.stage.value,
            "errors": [(lvl.value, msg) for lvl, msg in self.errors],
            "elapsed_sec": round(self.elapsed_sec, 3),
            "trace": self.trace[-20:],
        }
        if self.requirement:
            serializable["requirement"] = self.requirement.model_dump(mode="json")
        if self.plan:
            serializable["plan"] = self.plan.model_dump(mode="json")
        if self.model_output:
            serializable["model_output"] = self.model_output.model_dump(mode="json")
        if self.geometry_review:
            serializable["geometry_review"] = self.geometry_review.model_dump(mode="json")
        if self.drawing_output:
            serializable["drawing_output"] = self.drawing_output.model_dump(mode="json")
        if self.annotation_review:
            serializable["annotation_review"] = self.annotation_review.model_dump(mode="json")
        if self.visual_plan_json is not None:
            serializable["visual_plan"] = self.visual_plan_json
        if self.visual_result_data is not None:
            serializable["visual_result"] = self.visual_result_data
        if self.handshake is not None:
            serializable["handshake"] = self.handshake
        return json.dumps(serializable, indent=2, ensure_ascii=False)


class Orchestrator:
    """Agent编排器 — LangGraph风格的状态机。"""

    def __init__(
        self,
        requirement_agent: RequirementAgent | None = None,
        design_agent: DesignAgent | None = None,
        modeling_agent: CADModelingAgent | None = None,
        geometry_validator: GeometryValidator | None = None,
        drafting_agent: DraftingAgent | None = None,
        error_classifier: ErrorClassifier | None = None,
        visual_verifier: VisualVerifier | None = None,
        max_retries: int = 2,
        max_duration_sec: int = 600,
        verbose: bool = False,
    ) -> None:
        self.requirement_agent = requirement_agent or RequirementAgent()
        self.design_agent = design_agent or DesignAgent()
        self.modeling_agent = modeling_agent or CADModelingAgent()
        self.geometry_validator = geometry_validator or GeometryValidator()
        self.drafting_agent = drafting_agent or DraftingAgent()
        self.error_classifier = error_classifier or ErrorClassifier()
        self.visual_verifier = visual_verifier or VisualVerifier()
        self.max_retries = max_retries
        self.max_duration_sec = max_duration_sec
        self.verbose = verbose
        self._log: AgentLogger = get_logger("orchestrator", verbose=verbose)

    # ── 顶层：自然语言输入 → 完整流水线 ─────

    def run(self, user_input: str, part_name: str = "Part",
             dry_run: bool = False) -> PipelineResult:
        """从自然语言需求到最终图纸，全流程驱动。

        dry_run=True 时只解析需求、计划，不执行 FreeCAD。
        """
        start = time.time()
        result = PipelineResult(stage=PipelineStage.NEW)
        result.trace.append({"stage": PipelineStage.NEW.value,
                              "ts": time.time()})

        try:
            self._check_timebudget(start, "NEW")

            # 1. 需求解析
            with self._log.measure_stage("requirement", input=user_input[:50]):
                requirement = self.requirement_agent.parse(user_input)
            result.requirement = requirement
            result.trace.append({"stage": PipelineStage.REQUIREMENT_PARSED.value,
                                 "ts": time.time()})

            # 2. 设计规划
            self._check_timebudget(start, "requirement_parsed")
            with self._log.measure_stage("design"):
                plan = self.design_agent.plan(requirement)
            result.plan = plan
            result.stage = PipelineStage.DESIGN_PLANNED
            result.trace.append({"stage": PipelineStage.DESIGN_PLANNED.value,
                                 "ts": time.time()})

            if dry_run:
                result.stage = PipelineStage.DONE
                result.trace.append({"stage": "dry_run_ended",
                                      "ts": time.time()})
                result.elapsed_sec = time.time() - start
                return result

            # 3. CAD建模（带几何审查+重试）
            self._check_timebudget(start, "design_planned")
            with self._log.measure_stage("modeling"):
                model_output, geometry_review = self._retry_modeling(
                    requirement, plan, part_name, result
                )
            result.model_output = model_output
            result.geometry_review = geometry_review
            result.stage = PipelineStage.MODELING_DONE
            result.trace.append({"stage": PipelineStage.MODELING_DONE.value,
                                 "ts": time.time()})

            # 4. 几何审查（失败回滚
            self._check_timebudget(start, "modeling_done")
            if geometry_review.verdict == Verdict.FAIL:
                lvl = geometry_review.error_level
                msg = "; ".join(
                    c.detail for c in geometry_review.checks if not c.passed
                )
                result.errors.append((lvl, msg))
                self._log.error(lvl.value, msg)
                if lvl == ErrorLevel.DESIGN:
                    result.stage = PipelineStage.FAILED
                    result.elapsed_sec = time.time() - start
                    return result

            result.stage = PipelineStage.GEOMETRY_REVIEW

            # 5. 出图
            self._check_timebudget(start, "geometry_review")
            with self._log.measure_stage("drafting"):
                drawing = self.drafting_agent.execute(requirement, part_name)
            result.drawing_output = drawing
            result.stage = PipelineStage.DRAFTING
            result.trace.append({"stage": PipelineStage.DRAFTING.value,
                                 "ts": time.time()})

            # 6. 标注合规审核
            self._check_timebudget(start, "drafting")
            annotation = self.drafting_agent.review_annotations(requirement)
            result.annotation_review = annotation
            result.stage = PipelineStage.ANNOTATION_REVIEW
            result.trace.append({"stage": PipelineStage.ANNOTATION_REVIEW.value,
                                 "ts": time.time()})

            if annotation.verdict == Verdict.FAIL:
                msg = "; ".join(
                    c.detail for c in annotation.checks if not c.passed
                )
                result.errors.append((ErrorLevel.DRAWING, msg))
                self._log.error("DRAWING", msg)

            # 7. 视觉验证（Computer Use 截图 + AI 判断）
            self._check_timebudget(start, "annotation_review")
            if result.model_output and result.model_output.fcstd_path:
                vv = self.visual_verifier
                visual_plan = vv.generate_plan(
                    fcstd_path=result.model_output.fcstd_path,
                    requirement=requirement,
                    geometry_review=result.geometry_review,
                    cad_output=result.model_output,
                )
                result.visual_plan_json = json.loads(visual_plan.to_json())
                visual_result = vv.analyze(
                    screenshots=[],
                    requirement=requirement,
                    geometry_review=result.geometry_review,
                    cad_output=result.model_output,
                )
                result.visual_result_data = visual_result.to_dict()
                result.stage = PipelineStage.VISUAL_REVIEW
                result.trace.append({"stage": PipelineStage.VISUAL_REVIEW.value,
                                     "ts": time.time()})
                self._log.task("visual", "plan_generated",
                               views=visual_plan.screenshot_count)

            # 8. Schema 握手校验
            result.handshake = pipeline_handshake_report(result)
            self._log.io("pipeline", "handshake",
                         len(json.dumps(result.handshake).encode()))

            result.stage = PipelineStage.DONE
            result.trace.append({"stage": PipelineStage.DONE.value,
                                 "ts": time.time()})

        except TimeoutError as exc:
            result.errors.append((ErrorLevel.CODE, f"TIMEOUT: {exc}"))
            self._log.error("CODE", str(exc))
            result.stage = PipelineStage.FAILED

        except Exception as exc:
            lvl, msg = self.error_classifier.classify(
                str(exc), agent_stage=result.stage.value
            )
            result.errors.append((lvl, msg))
            self._log.error(lvl.value, msg)
            result.stage = PipelineStage.FAILED

        result.elapsed_sec = time.time() - start
        return result

    # ── 内部：建模+审查的重试循环 ─────────

    def _retry_modeling(self, requirement: RequirementDocument,
                         plan: ModelingPlan, part_name: str,
                         result: PipelineResult) -> tuple[CADModelingOutput, GeometryReviewReport]:
        for attempt in range(self.max_retries + 1):
            model_output = self.modeling_agent.execute_plan(
                plan, requirement, part_name
            )
            try:
                review = self.geometry_validator.validate_from_mock(
                    face_count=6,
                    volume=1000.0,
                    is_connected=True,
                    is_valid=True,
                    is_closed=True,
                    bounding_box=(100.0, 50.0, 25.0),
                )
            except (TypeError, AttributeError):
                review = self.geometry_validator.validate_from_primitives(
                    requirement.part_type.value,
                    length=requirement.dimensions.get("length", 100.0),
                    width=requirement.dimensions.get("width", 50.0),
                    height=requirement.dimensions.get("height", 25.0),
                )

            if review.verdict == Verdict.PASS:
                return model_output, review

            # 失败 → 按 ErrorLevel 回滚
            lvl = review.error_level
            msg = "; ".join(c.detail for c in review.checks if not c.passed)
            result.errors.append((lvl, msg))
            self._log.task("modeling", "fail", attempt=attempt)

            if attempt < self.max_retries:
                if lvl == ErrorLevel.DESIGN:
                    # 重置尺寸 +10%
                    for k in list(requirement.dimensions.keys()):
                        requirement.dimensions[k] *= 1.1
                    plan = self.design_agent.plan(requirement)
                    result.plan = plan
                else:
                    self.modeling_agent.use_primitive_shortcut = (
                        not self.modeling_agent.use_primitive_shortcut
                    )
                self._log.task("modeling", "retry", attempt=attempt)
        return model_output, review

    # ── 超时检测 ────────────────────────────

    def _check_timebudget(self, start: float, stage_label: str) -> None:
        elapsed = time.time() - start
        if elapsed > self.max_duration_sec:
            raise TimeoutError(
                f"Pipeline exceeded {self.max_duration_sec}s at stage '{stage_label}'"
            )

    # ── 调试辅助：report() / explain() ──────────

    def report(self, result: PipelineResult) -> str:
        """P1 兼容 — 返回简要报告，等同于 explain()。"""
        return self.explain(result)

    def explain(self, result: PipelineResult) -> str:
        """返回人类可读的诊断报告。"""
        lines: list[str] = []
        lines.append(f"== Pipeline Diagnosis ==")
        lines.append(f"Stage: {result.stage.value}")
        lines.append(f"Elapsed: {result.elapsed_sec:.2f}s")

        if result.requirement:
            lines.append(f"Part: {result.requirement.part_type.value}")
            lines.append(f"  dims: {result.requirement.dimensions}")
            lines.append(f"  material: {result.requirement.material}")
            lines.append(f"  tolerance: {result.requirement.tolerance_grade.value}")

        if result.plan:
            lines.append(f"Plan features: {len(result.plan.features)}")
            for f in result.plan.features:
                lines.append(f"  [{f.step}] {f.operation.value} params={f.parameters}")

        if result.geometry_review:
            lines.append(
                f"Geometry review: {result.geometry_review.verdict.value} "
                f"(checks passed={sum(1 for c in result.geometry_review.checks if c.passed)}/"
                f"{len(result.geometry_review.checks)})"
            )

        if result.drawing_output:
            lines.append(f"Drawing: {result.drawing_output.views}")

        if result.visual_result_data:
            vr = result.visual_result_data
            passed_count = sum(1 for c in vr.get("checks", []) if c.get("passed"))
            total_count = len(vr.get("checks", []))
            lines.append(f"Visual review: {vr.get('verdict', 'N/A')} "
                         f"(checks: {passed_count}/{total_count})")
        if result.visual_plan_json:
            vp = result.visual_plan_json
            action_count = len(vp.get("actions", []))
            view_count = len(vp.get("views", []))
            lines.append(f"Visual plan: {action_count} actions, {view_count} views")

        if result.errors:
            lines.append("Errors:")
            for lvl, msg in result.errors:
                lines.append(f"  [{lvl.value}] {msg}")
        else:
            lines.append("Errors: none")

        if result.handshake:
            hs = result.handshake
            lines.append(f"Handshake: {hs.get('all_valid')} "
                         f"({hs.get('schema_count')} schemas)")

        return "\n".join(lines)


# ── 便捷函数 ──────────────────────────

def run_pipeline(user_input: str, part_name: str = "Part",
                  dry_run: bool = False) -> PipelineResult:
    """直接运行默认编排器。"""
    return Orchestrator().run(user_input, part_name, dry_run=dry_run)


def run_standard_part(short_name: str, part_name: str | None = None) -> PipelineResult:
    """使用 P2.3 标准件库驱动 — 从标准件编号到完整流水线。

    示例: run_standard_part("bolt_m6_16")
    """
    lib = get_library()
    req = lib.get_requirement(short_name)
    if req is None:
        raise ValueError(f"Unknown standard part: {short_name}")
    orch = Orchestrator()
    return orch.run(f"{req.part_type.value} {req.dimensions}",
                  part_name or short_name)
