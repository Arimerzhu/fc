"""视觉验证集成层 — 连接 Orchestrator PipelineResult 与 VisualVerifier。

提供高层 API:
  verify_pipeline_result(result) -> VisualVerificationResult
  bridge_orchestrator_to_visual(orchestrator, user_input) -> full pipeline + visual

"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_schemas import (
    CADModelingOutput,
    ErrorLevel,
    GeometryReviewReport,
    RequirementDocument,
    Verdict,
)
from .orchestrator import Orchestrator, PipelineResult, PipelineStage
from .visual_verifier import (
    ScreenshotResult,
    VisualCheck,
    VisualVerificationPlan,
    VisualVerificationResult,
    VisualVerifier,
    ViewAngle,
)


# ── 集成结果 ────────────────────────────────────────────────────

@dataclass
class IntegratedVerificationResult:
    """集成验证结果 — 合并流水线 + 视觉验证。"""
    pipeline_stage: PipelineStage
    pipeline_passed: bool
    visual_result: VisualVerificationResult | None
    visual_plan: VisualVerificationPlan | None
    overall_verdict: Verdict
    error_level: ErrorLevel
    summary: str

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "pipeline_stage": self.pipeline_stage.value,
            "pipeline_passed": self.pipeline_passed,
            "overall_verdict": self.overall_verdict.value,
            "error_level": self.error_level.value,
            "summary": self.summary,
        }
        if self.visual_result:
            result["visual"] = self.visual_result.to_dict()
        if self.visual_plan:
            result["visual_plan_action_count"] = len(self.visual_plan.actions)
            result["visual_plan_screenshots"] = self.visual_plan.screenshot_count
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# ── 核心集成函数 ────────────────────────────────────────────────


def verify_pipeline_result(
    pipeline_result: PipelineResult,
    views: list[ViewAngle] | None = None,
    include_close: bool = True,
) -> IntegratedVerificationResult:
    """从 PipelineResult 生成视觉验证计划和结果。

    如果没有 FCStd 文件路径（流水线未到达建模阶段），
    则跳过视觉验证，返回基于流水线状态的集成结果。
    """
    pipeline_passed = pipeline_result.stage == PipelineStage.DONE
    requirement = pipeline_result.requirement
    geometry_review = pipeline_result.geometry_review
    model_output = pipeline_result.model_output

    # 提取 FCStd 路径
    fcstd_path = ""
    if model_output and model_output.fcstd_path:
        fcstd_path = model_output.fcstd_path

    vv = VisualVerifier(views=views, include_close=include_close)

    # 如果没有模型文件，无法进行视觉验证
    if not fcstd_path or not os.path.exists(fcstd_path):
        visual_plan = None
        visual_result = None
        if fcstd_path:
            visual_plan = vv.generate_plan(
                fcstd_path=fcstd_path,
                requirement=requirement,
                geometry_review=geometry_review,
                cad_output=model_output,
            )
        overall = pipeline_result.stage
        verdict = Verdict.PASS if pipeline_passed else Verdict.FAIL
        error_level = ErrorLevel.NONE
        if not pipeline_passed:
            errors = pipeline_result.errors
            if errors:
                error_level = errors[-1][0] if errors else ErrorLevel.CODE
        summary = f"流水线: {overall.value}, 视觉验证: 跳过(无FCStd文件)"
        return IntegratedVerificationResult(
            pipeline_stage=overall,
            pipeline_passed=pipeline_passed,
            visual_result=visual_result,
            visual_plan=visual_plan,
            overall_verdict=verdict,
            error_level=error_level,
            summary=summary,
        )

    # 有模型文件 — 生成计划 + 执行可自动化检查
    visual_plan = vv.generate_plan(
        fcstd_path=fcstd_path,
        requirement=requirement,
        geometry_review=geometry_review,
        cad_output=model_output,
    )

    # 执行可自动化的检查（不含截图视觉分析）
    empty_screenshots: list[ScreenshotResult] = []
    visual_result = vv.analyze(
        screenshots=empty_screenshots,
        requirement=requirement,
        geometry_review=geometry_review,
        cad_output=model_output,
    )

    # 综合判定
    both_pass = pipeline_passed and visual_result.verdict == Verdict.PASS
    overall_verdict = Verdict.PASS if both_pass else Verdict.FAIL

    # 取最严重的 error_level
    levels = [visual_result.error_level]
    if pipeline_result.errors:
        levels.extend(lvl for lvl, _ in pipeline_result.errors)
    error_level = _max_error_level(levels)

    summary_parts = [
        f"流水线: {pipeline_result.stage.value}",
        f"几何审查: {geometry_review.verdict.value if geometry_review else "N/A"}",
        f"视觉验证: {visual_result.verdict.value}",
        f"综合判定: {overall_verdict.value}",
    ]
    summary = " | ".join(summary_parts)

    return IntegratedVerificationResult(
        pipeline_stage=pipeline_result.stage,
        pipeline_passed=pipeline_passed,
        visual_result=visual_result,
        visual_plan=visual_plan,
        overall_verdict=overall_verdict,
        error_level=error_level,
        summary=summary,
    )


def bridge_orchestrator_to_visual(
    user_input: str,
    part_name: str = "Part",
    dry_run: bool = False,
    views: list[ViewAngle] | None = None,
) -> IntegratedVerificationResult:
    """完整流水线 + 视觉验证一体化入口。

    运行 Orchestrator 流水线，然后自动执行视觉验证。
    返回集成结果，包含流水线状态和视觉验证报告。
    """
    orch = Orchestrator()
    pipeline_result = orch.run(user_input, part_name, dry_run=dry_run)
    return verify_pipeline_result(pipeline_result, views=views)


# ── 辅助函数 ────────────────────────────────────────────────────

_ERROR_SEVERITY = {
    ErrorLevel.NONE: 0,
    ErrorLevel.DRAWING: 1,
    ErrorLevel.CODE: 2,
    ErrorLevel.DESIGN: 3,
}


def _max_error_level(levels: list[ErrorLevel]) -> ErrorLevel:
    if not levels:
        return ErrorLevel.NONE
    return max(levels, key=lambda lvl: _ERROR_SEVERITY.get(lvl, 0))


def generate_codex_visual_script(
    pipeline_result: PipelineResult,
) -> str | None:
    """从 PipelineResult 生成 Codex Computer Use JavaScript 脚本。

    返回 None 如果没有可验证的模型文件。
    """
    if not pipeline_result.model_output:
        return None
    fcstd_path = pipeline_result.model_output.fcstd_path
    if not fcstd_path:
        return None

    vv = VisualVerifier()
    plan = vv.generate_plan(
        fcstd_path=fcstd_path,
        requirement=pipeline_result.requirement,
        geometry_review=pipeline_result.geometry_review,
        cad_output=pipeline_result.model_output,
    )
    return vv.generate_codex_guide(plan)


def export_visual_plan_json(
    pipeline_result: PipelineResult,
    output_path: str | None = None,
) -> str:
    """导出视觉验证计划为 JSON 文件。

    返回 JSON 文件路径。
    """
    if not pipeline_result.model_output:
        return ""
    fcstd_path = pipeline_result.model_output.fcstd_path
    if not fcstd_path:
        return ""

    vv = VisualVerifier()
    plan = vv.generate_plan(
        fcstd_path=fcstd_path,
        requirement=pipeline_result.requirement,
        geometry_review=pipeline_result.geometry_review,
        cad_output=pipeline_result.model_output,
    )

    if output_path is None:
        output_path = str(Path(fcstd_path).with_suffix(".visual_plan.json"))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(plan.to_json())

    return output_path
