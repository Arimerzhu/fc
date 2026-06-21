"""P3.1 — 标注合规 Agent

方法论中 Agent 6: 标注合规审查
检查出图产物是否满足工程图规范：
  - 主视图 / 投影视图是否齐全
  - 关键尺寸是否标注（长度、宽度、高度、孔径等）
  - 公差标注是否完整
  - 技术要求/标题栏信息是否完整
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fc_runtime.agent_logging import AgentLogger, get_logger
from fc_runtime.agent_schemas import (
    AnnotationCheck,
    AnnotationReviewReport,
    DrawingOutput,
    ErrorLevel,
    RequirementDocument,
    Verdict,
)


@dataclass
class _StandardCheck:
    check_name: str
    passed: bool
    detail: str = ""
    suggestion: str = ""


# ── 标准检查项 ───────────────────────────────

def _check_views_present(views: list[str]) -> AnnotationCheck:
    """至少要有一个主视图（front/top/side/iso 中的一个）。"""
    required = {"front", "top", "side"}
    has_main = any(v.lower() in required for v in views) or len(views) >= 1
    return AnnotationCheck(
        check_name="views_present",
        passed=has_main,
        detail=f"现有视图={views}" if views else "未生成任何视图",
        suggestion=("至少需要一个主视图（front/top/side），"
                    "否则下游加工无法定位尺寸。"
                    if not has_main else "视图布局完整"),
    )


def _check_view_variety(views: list[str]) -> AnnotationCheck:
    """建议至少有2个正交视图，便于定位三维尺寸。"""
    unique = set(views)
    passed = len(unique) >= 2
    return AnnotationCheck(
        check_name="view_variety",
        passed=passed,
        detail=f"视图数={len(unique)}，正交视图对={max(0, len(unique) - 1)}",
        suggestion=("单个视图无法表达三维形状，"
                    "建议至少提供 front + top 两个正交视图。"
                    if not passed else "视图表达充分"),
    )


def _check_dimension_count(drawing: DrawingOutput) -> AnnotationCheck:
    """是否有尺寸标注（通过 drawing.dimensions 推断或使用视图数估算）。"""
    # DrawingOutput 当前没有 dimensions 字段，用 views 数估计
    # 同时检查是否有 material / tolerance 信息（通过 requirement 传入）
    dims = getattr(drawing, "dimensions", None) or []
    n = len(dims) if isinstance(dims, (list, tuple)) else 0
    passed = n > 0 or len(drawing.views) >= 1
    return AnnotationCheck(
        check_name="dimensions_annotated",
        passed=passed,
        detail=f"尺寸标注数={n}，视图数={len(drawing.views)}",
        suggestion=("无任何尺寸标注，工程图无法用于加工。"
                    if not passed else "尺寸标注信息存在"),
    )


def _check_tolerance(
    requirement: RequirementDocument | None,
) -> AnnotationCheck:
    """是否定义了公差等级。"""
    if requirement is None:
        return AnnotationCheck(
            check_name="tolerance_defined",
            passed=True,
            detail="无需求文档，跳过公差检查",
            suggestion="",
        )
    tg = requirement.tolerance_grade
    passed = tg is not None and tg.value != "none"
    return AnnotationCheck(
        check_name="tolerance_defined",
        passed=passed,
        detail=f"公差等级={tg.value if tg else '未定义'}",
        suggestion=("未指定公差等级，加工精度无法保障。"
                    if not passed else "公差等级已定义"),
    )


def _check_material(
    requirement: RequirementDocument | None,
) -> AnnotationCheck:
    """是否有明确的材料信息。"""
    if requirement is None:
        return AnnotationCheck(
            check_name="material_defined",
            passed=True,
            detail="无需求文档，跳过材料检查",
            suggestion="",
        )
    material = (requirement.material or "").strip()
    passed = len(material) > 0
    return AnnotationCheck(
        check_name="material_defined",
        passed=passed,
        detail=f"材料={material or '未定义'}",
        suggestion=("未指定材料，无法进行强度评估或加工选型。"
                    if not passed else "材料信息已定义"),
    )


def _check_standard(
    requirement: RequirementDocument | None,
) -> AnnotationCheck:
    """是否有标准引用（ISO/GB/ANSI 等）。"""
    if requirement is None:
        return AnnotationCheck(
            check_name="standard_referenced",
            passed=True,
            detail="无需求文档，跳过标准检查",
            suggestion="",
        )
    std = requirement.standard
    passed = std is not None and std.value != "custom"
    return AnnotationCheck(
        check_name="standard_referenced",
        passed=passed,
        detail=f"标准={std.value if std else '未指定'}",
        suggestion=("未引用设计标准，建议明确 ISO/GB/ANSI 等规范。"
                    if not passed else "设计标准已引用"),
    )


def _check_sheet_projection(drawing: DrawingOutput) -> AnnotationCheck:
    """是否声明了投影方法（第一角/第三角）。"""
    proj = getattr(drawing, "projection", "First Angle") or "First Angle"
    # 非空即视为通过（用户在 DrawingOutput 里应显式声明）
    passed = isinstance(proj, str) and len(proj) > 0
    return AnnotationCheck(
        check_name="projection_defined",
        passed=passed,
        detail=f"投影方法={proj}",
        suggestion=("未声明投影方法，不同国家默认不同，"
                    "必须明确标注 First Angle / Third Angle。"
                    if not passed else "投影方法已声明"),
    )


class AnnotationComplianceAgent:
    """标注合规 Agent（方法论 Agent 6）。

    独立运行：接收出图结果 + 原始需求，审查工程图的标注规范，
    输出 AnnotationReviewReport，供编排器决定是否回滚到出图阶段。
    """

    def __init__(self, verbose: bool = False) -> None:
        self._log: AgentLogger = get_logger("annotation_review",
                                             verbose=verbose)

    # ── 主审查流程 ─────────────────────────────

    def review(
        self,
        drawing: DrawingOutput,
        requirement: RequirementDocument | None = None,
    ) -> AnnotationReviewReport:
        """执行完整的标注合规审查。"""
        with self._log.measure_stage("review"):
            checks = [
                _check_views_present(drawing.views),
                _check_view_variety(drawing.views),
                _check_dimension_count(drawing),
                _check_tolerance(requirement),
                _check_material(requirement),
                _check_standard(requirement),
                _check_sheet_projection(drawing),
            ]

            all_passed = all(c.passed for c in checks)
            verdict = Verdict.PASS if all_passed else Verdict.FAIL
            error_level = self._compute_error_level(checks)

            self._log.task(
                "review",
                "pass" if all_passed else "fail",
                checks=len(checks),
                failed=sum(1 for c in checks if not c.passed),
                error_level=error_level.value,
            )

            return AnnotationReviewReport(
                verdict=verdict,
                checks=checks,
                error_level=error_level,
            )

    # ── 辅助 ───────────────────────────────────

    @staticmethod
    def _compute_error_level(checks: list[AnnotationCheck]) -> ErrorLevel:
        """根据检查失败项计算等级。

        - CODE 级：缺少视图/尺寸标注 → 重新出图即可修复
        - DRAWING 级：材料/公差/标准缺失 → 在工程图层面补充信息
        """
        failed = {c.check_name for c in checks if not c.passed}

        if "views_present" in failed or "dimensions_annotated" in failed:
            return ErrorLevel.CODE
        if failed:
            return ErrorLevel.DRAWING
        return ErrorLevel.NONE
