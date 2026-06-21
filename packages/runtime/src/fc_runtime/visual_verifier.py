"""视觉验证器 — 通过 Computer Use 截图 + AI 视觉判断模型正确性。

方法论v1.0 补充：几何拓扑校验只能验证数学属性，
无法判断"模型看起来对不对"。本模块补上这个盲区。

两种运行模式：
  A. Plan 模式 — 生成结构化动作序列（JSON），供 Codex Computer Use 执行
  B. Guide 模式 — 生成人类可读的分步指令，供手动操作

依赖：无 FreeCAD 依赖。仅依赖 agent_schemas（Pydantic）。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .agent_schemas import (
    CADModelingOutput,
    ErrorLevel,
    GeometryReviewReport,
    RequirementDocument,
    Verdict,
)


# ── 动作类型 ────────────────────────────────────────────────────

class ActionType(str, Enum):
    """Computer Use 自动化动作类型。"""
    LAUNCH_APP = "launch_app"
    FIND_WINDOW = "find_window"
    OPEN_FILE = "open_file"
    SET_VIEW = "set_view"
    ROTATE_VIEW = "rotate_view"
    ZOOM_FIT = "zoom_fit"
    CAPTURE_SCREENSHOT = "capture_screenshot"
    CLOSE_APP = "close_app"
    WAIT = "wait"


class ViewAngle(str, Enum):
    """标准视图角度。"""
    ISOMETRIC = "isometric"
    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


# ── 数据结构 ────────────────────────────────────────────────────

@dataclass
class CUAction:
    """单个 Computer Use 自动化动作。"""
    action_type: ActionType
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    timeout_ms: int = 5000

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "params": self.params,
            "description": self.description,
            "timeout_ms": self.timeout_ms,
        }


@dataclass
class VisualVerificationPlan:
    """视觉验证计划 — 一组有序的 Computer Use 动作。"""
    fcstd_path: str
    views: list[ViewAngle]
    actions: list[CUAction]
    expected_properties: dict[str, Any] = field(default_factory=dict)
    part_type: str = ""

    def to_json(self) -> str:
        return json.dumps({
            "fcstd_path": self.fcstd_path,
            "views": [v.value for v in self.views],
            "expected_properties": self.expected_properties,
            "part_type": self.part_type,
            "actions": [act.to_dict() for act in self.actions],
        }, indent=2, ensure_ascii=False)

    @property
    def screenshot_count(self) -> int:
        return sum(1 for act in self.actions
                   if act.action_type == ActionType.CAPTURE_SCREENSHOT)


@dataclass
class ScreenshotResult:
    """截图结果。"""
    view: ViewAngle
    screenshot_id: str = ""
    description: str = ""


@dataclass
class VisualCheck:
    """单项视觉检查。"""
    check_name: str
    passed: bool
    detail: str = ""
    suggestion: str = ""


@dataclass
class VisualVerificationResult:
    """视觉验证结果。"""
    verdict: Verdict
    checks: list[VisualCheck]
    screenshots: list[ScreenshotResult] = field(default_factory=list)
    error_level: ErrorLevel = ErrorLevel.NONE
    elapsed_sec: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "checks": [
                {"check_name": c.check_name, "passed": c.passed,
                 "detail": c.detail, "suggestion": c.suggestion}
                for c in self.checks
            ],
            "screenshot_count": len(self.screenshots),
            "error_level": self.error_level.value,
            "elapsed_sec": round(self.elapsed_sec, 3),
            "summary": self.summary,
        }

# ── 常量与推断辅助 ────────────────────────────────────────────

_FREECAD_APP_NAMES = ["FreeCAD", "FreeCAD.exe"]
_DEFAULT_VIEWPORT_DELAY_MS = 2000


def _infer_expected_views(part_type: str,
                          dimensions: dict[str, float]) -> list[ViewAngle]:
    """根据零件类型推断最佳观察角度。"""
    flat_types = {"plate", "bracket", "flange"}
    long_types = {"shaft", "cylinder"}
    symmetric_types = {"sphere", "torus", "gear"}
    if part_type in flat_types:
        return [ViewAngle.ISOMETRIC, ViewAngle.TOP, ViewAngle.FRONT]
    if part_type in long_types:
        return [ViewAngle.ISOMETRIC, ViewAngle.FRONT, ViewAngle.TOP]
    if part_type in symmetric_types:
        return [ViewAngle.ISOMETRIC, ViewAngle.FRONT]
    return [ViewAngle.ISOMETRIC, ViewAngle.FRONT, ViewAngle.TOP, ViewAngle.RIGHT]


def _estimate_aspect_ratio(part_type: str,
                           dimensions: dict[str, float]) -> str:
    """粗略估计零件的宽高比描述。"""
    length = dimensions.get("length", dimensions.get("diameter", 100.0))
    width = dimensions.get("width", dimensions.get("diameter", length))
    height = dimensions.get("height", dimensions.get("thickness", length))
    if height < length * 0.2 and height < width * 0.2:
        return "flat"
    if length > width * 3 and length > height * 3:
        return "elongated"
    if abs(length - width) < length * 0.2 and abs(length - height) < length * 0.2:
        return "cubic"
    return "irregular"


def _infer_visual_properties(
    part_type: str,
    dimensions: dict[str, float],
    geometry_review: GeometryReviewReport | None = None,
) -> dict[str, Any]:
    """从需求和几何审查中推断视觉验证的预期属性。"""
    props: dict[str, Any] = {
        "part_type": part_type,
        "dimensions": dimensions,
    }
    if dimensions:
        max_dim = max(dimensions.values())
        props["expected_aspect_ratio"] = _estimate_aspect_ratio(part_type, dimensions)
        props["max_dimension_mm"] = max_dim
    if geometry_review:
        props["geometry_verdict"] = geometry_review.verdict.value
        passed_checks = sum(1 for c in geometry_review.checks if c.passed)
        total_checks = len(geometry_review.checks)
        props["geometry_checks_passed"] = f"{passed_checks}/{total_checks}"
    return props

# ── 动作生成器 ──────────────────────────────────────────────────


def _make_launch_action() -> CUAction:
    return CUAction(
        action_type=ActionType.LAUNCH_APP,
        params={"app_names": _FREECAD_APP_NAMES},
        description="启动 FreeCAD 应用",
        timeout_ms=15000,
    )


def _make_find_window_action() -> CUAction:
    return CUAction(
        action_type=ActionType.FIND_WINDOW,
        params={"title_contains": "FreeCAD"},
        description="定位 FreeCAD 主窗口",
        timeout_ms=5000,
    )


def _make_open_file_action(fcstd_path: str) -> CUAction:
    abs_path = str(Path(fcstd_path).resolve())
    return CUAction(
        action_type=ActionType.OPEN_FILE,
        params={"file_path": abs_path, "method": "drag_drop_or_menu"},
        description=f"打开 FCStd 文件: {abs_path}",
        timeout_ms=10000,
    )


_VIEW_NAME_MAP = {
    ViewAngle.ISOMETRIC: "Axonometric",
    ViewAngle.FRONT: "Front",
    ViewAngle.BACK: "Rear",
    ViewAngle.LEFT: "Left",
    ViewAngle.RIGHT: "Right",
    ViewAngle.TOP: "Top",
    ViewAngle.BOTTOM: "Bottom",
}

_VIEW_SHORTCUT_MAP = {
    ViewAngle.ISOMETRIC: "Control_L+KP_0",
    ViewAngle.FRONT: "KP_1",
    ViewAngle.BACK: "Control_L+KP_1",
    ViewAngle.LEFT: "KP_3",
    ViewAngle.RIGHT: "Control_L+KP_3",
    ViewAngle.TOP: "KP_7",
    ViewAngle.BOTTOM: "Control_L+KP_7",
}


def _make_set_view_action(view: ViewAngle) -> CUAction:
    return CUAction(
        action_type=ActionType.SET_VIEW,
        params={
            "view": view.value,
            "freecad_view_name": _VIEW_NAME_MAP.get(view, ""),
            "shortcut": _VIEW_SHORTCUT_MAP.get(view, ""),
        },
        description=f"切换到 {view.value} 视图",
        timeout_ms=3000,
    )


def _make_zoom_fit_action() -> CUAction:
    return CUAction(
        action_type=ActionType.ZOOM_FIT,
        params={"shortcut": "V, F"},
        description="缩放到适合窗口",
        timeout_ms=2000,
    )


def _make_capture_action(view: ViewAngle, index: int) -> CUAction:
    return CUAction(
        action_type=ActionType.CAPTURE_SCREENSHOT,
        params={"view": view.value, "label": f"view_{view.value}_{index}"},
        description=f"截取 {view.value} 视图",
        timeout_ms=5000,
    )


def _make_close_action() -> CUAction:
    return CUAction(
        action_type=ActionType.CLOSE_APP,
        params={"save_before_close": False},
        description="关闭 FreeCAD",
        timeout_ms=5000,
    )


def _make_wait_action(delay_ms: int, reason: str = "") -> CUAction:
    desc = f"等待 {delay_ms}ms"
    if reason:
        desc = f"{desc} ({reason})"
    return CUAction(
        action_type=ActionType.WAIT,
        params={"delay_ms": delay_ms, "reason": reason},
        description=desc,
        timeout_ms=delay_ms + 1000,
    )

# ── 视觉检查分析 ────────────────────────────────────────────────


def _analyze_dimension_consistency(
    dimensions: dict[str, float],
    geometry_review: GeometryReviewReport | None,
) -> VisualCheck:
    if not dimensions:
        return VisualCheck(
            check_name="dimension_consistency", passed=True,
            detail="无尺寸信息可校验",
        )
    if geometry_review is None:
        return VisualCheck(
            check_name="dimension_consistency", passed=True,
            detail="无几何审查报告，跳过",
        )
    geo_ok = geometry_review.verdict == Verdict.PASS
    return VisualCheck(
        check_name="dimension_consistency", passed=geo_ok,
        detail=f"几何审查: {geometry_review.verdict.value}, 需求尺寸: {dimensions}",
        suggestion="" if geo_ok else "几何审查未通过，模型尺寸可能与需求不符",
    )


def _analyze_geometry_pass_rate(
    geometry_review: GeometryReviewReport | None,
) -> VisualCheck:
    if geometry_review is None:
        return VisualCheck(
            check_name="geometry_pass_rate", passed=True,
            detail="无几何审查报告",
        )
    total = len(geometry_review.checks)
    passed = sum(1 for c in geometry_review.checks if c.passed)
    rate = passed / total if total > 0 else 1.0
    ok = rate >= 0.8
    return VisualCheck(
        check_name="geometry_pass_rate", passed=ok,
        detail=f"几何检查通过率: {passed}/{total} ({rate:.0%})",
        suggestion="" if ok else "几何检查通过率低于80%",
    )


def _analyze_aspect_ratio(
    part_type: str, dimensions: dict[str, float],
) -> VisualCheck:
    if not dimensions:
        return VisualCheck(
            check_name="aspect_ratio", passed=True, detail="无尺寸信息",
        )
    ratio_desc = _estimate_aspect_ratio(part_type, dimensions)
    mismatches: list[str] = []
    if part_type == "plate" and "elongated" in ratio_desc:
        mismatches.append("plate不应是细长形")
    if part_type == "shaft" and "flat" in ratio_desc:
        mismatches.append("shaft不应是扁平形")
    if part_type == "sphere" and "cubic" not in ratio_desc:
        mismatches.append("sphere应近似等尺寸")
    ok = len(mismatches) == 0
    return VisualCheck(
        check_name="aspect_ratio", passed=ok,
        detail=f"宽高比: {ratio_desc}, 零件类型: {part_type}",
        suggestion="; ".join(mismatches) if mismatches else "宽高比与零件类型匹配",
    )


def _analyze_bounding_box_reasonable(
    dimensions: dict[str, float],
    cad_output: CADModelingOutput | None,
) -> VisualCheck:
    if cad_output is None or not dimensions:
        return VisualCheck(
            check_name="bounding_box_reasonable", passed=True,
            detail="无 CAD 输出或尺寸信息",
        )
    bbox = cad_output.bounding_box
    if all(v < 0.001 for v in bbox):
        return VisualCheck(
            check_name="bounding_box_reasonable", passed=False,
            detail=f"bounding box 为零: {bbox}",
            suggestion="模型可能为空或退化",
        )
    dim_values = sorted(dimensions.values(), reverse=True)
    bbox_values = sorted(bbox, reverse=True)
    tolerance = 0.3
    mismatches: list[str] = []
    for i, (expected, actual) in enumerate(zip(dim_values[:3], bbox_values[:3])):
        ratio = actual / expected if expected > 0 else 0
        if ratio < (1 - tolerance) or ratio > (1 + tolerance):
            mismatches.append(
                f"维度{i+1}: 期望{expected:.1f}mm, 实际bbox={actual:.1f}mm (比率={ratio:.2f})")
    ok = len(mismatches) == 0
    return VisualCheck(
        check_name="bounding_box_reasonable", passed=ok,
        detail=f"bbox={bbox}",
        suggestion="; ".join(mismatches) if mismatches else "bbox与需求尺寸匹配",
    )

# ── 主类 ────────────────────────────────────────────────────────


class VisualVerifier:
    """视觉验证器 — 通过 Computer Use 截图验证 FreeCAD 模型。

    使用方式:
        vv = VisualVerifier()
        plan = vv.generate_plan(fcstd_path, requirement, geometry_review)
        actions_json = plan.to_json()
        # Computer Use 执行后:
        result = vv.analyze(screenshots, requirement, geometry_review, cad_output)
    """

    DEFAULT_VIEWS = [
        ViewAngle.ISOMETRIC, ViewAngle.FRONT,
        ViewAngle.TOP, ViewAngle.RIGHT,
    ]

    def __init__(
        self,
        views: list[ViewAngle] | None = None,
        include_close: bool = True,
        viewport_delay_ms: int = _DEFAULT_VIEWPORT_DELAY_MS,
    ) -> None:
        self.views = views or self.DEFAULT_VIEWS
        self.include_close = include_close
        self.viewport_delay_ms = viewport_delay_ms

    # ── 计划生成 ────────────────────────────────────────────

    def generate_plan(
        self,
        fcstd_path: str,
        requirement: RequirementDocument | None = None,
        geometry_review: GeometryReviewReport | None = None,
        cad_output: CADModelingOutput | None = None,
    ) -> VisualVerificationPlan:
        """生成完整的 Computer Use 视觉验证计划。"""
        part_type = requirement.part_type.value if requirement else "unknown"
        dimensions = requirement.dimensions if requirement else {}
        views = self._select_views(part_type, dimensions)
        expected = _infer_visual_properties(part_type, dimensions, geometry_review)
        actions = self._build_action_sequence(fcstd_path, views)
        return VisualVerificationPlan(
            fcstd_path=fcstd_path, views=views, actions=actions,
            expected_properties=expected, part_type=part_type,
        )

    def _select_views(self, part_type: str,
                      dimensions: dict[str, float]) -> list[ViewAngle]:
        inferred = _infer_expected_views(part_type, dimensions)
        if self.views:
            seen: set[ViewAngle] = set()
            merged: list[ViewAngle] = []
            for v in self.views + inferred:
                if v not in seen:
                    seen.add(v)
                    merged.append(v)
            return merged[:6]
        return inferred[:6]

    def _build_action_sequence(self, fcstd_path: str,
                               views: list[ViewAngle]) -> list[CUAction]:
        actions: list[CUAction] = []
        actions.append(_make_launch_action())
        actions.append(_make_wait_action(3000, "等待 FreeCAD 启动"))
        actions.append(_make_find_window_action())
        actions.append(_make_open_file_action(fcstd_path))
        actions.append(_make_wait_action(2000, "等待文件加载"))
        actions.append(_make_zoom_fit_action())
        actions.append(_make_wait_action(1000, "等待视图缩放"))
        for i, view in enumerate(views):
            actions.append(_make_set_view_action(view))
            actions.append(_make_wait_action(self.viewport_delay_ms, "等待视图切换"))
            actions.append(_make_capture_action(view, i))
        if self.include_close:
            actions.append(_make_close_action())
        return actions
    # ── 结果分析 ────────────────────────────────────────────

    def analyze(
        self,
        screenshots: list[ScreenshotResult],
        requirement: RequirementDocument | None = None,
        geometry_review: GeometryReviewReport | None = None,
        cad_output: CADModelingOutput | None = None,
    ) -> VisualVerificationResult:
        """分析视觉验证结果。

        注意：真正的视觉判断需要 AI 查看截图。
        本方法执行所有可自动化的检查（几何一致性、尺寸匹配等），
        并标记需要 AI 视觉判断的检查项。
        """
        start = time.time()
        checks: list[VisualCheck] = []
        part_type = requirement.part_type.value if requirement else "unknown"
        dimensions = requirement.dimensions if requirement else {}

        checks.append(_analyze_dimension_consistency(dimensions, geometry_review))
        checks.append(_analyze_geometry_pass_rate(geometry_review))
        checks.append(_analyze_aspect_ratio(part_type, dimensions))
        checks.append(_analyze_bounding_box_reasonable(dimensions, cad_output))
        checks.append(VisualCheck(
            check_name="visual_inspection_needed", passed=True,
            detail=f"已截取 {len(screenshots)} 张视图，需 AI 视觉判断",
            suggestion="请用 AI 视觉能力检查: 形状正确性、特征位置、比例感观",
        ))

        all_ok = all(c.passed for c in checks
                     if c.check_name != "visual_inspection_needed")
        error_level = self._compute_error_level(checks)
        elapsed = time.time() - start
        summary = self._build_summary(checks, screenshots)

        return VisualVerificationResult(
            verdict=Verdict.PASS if all_ok else Verdict.FAIL,
            checks=checks, screenshots=screenshots,
            error_level=error_level, elapsed_sec=elapsed, summary=summary,
        )

    def _compute_error_level(self, checks: list[VisualCheck]) -> ErrorLevel:
        failed = [c for c in checks if not c.passed]
        if not failed:
            return ErrorLevel.NONE
        if any(c.check_name in ("dimension_consistency", "aspect_ratio")
               for c in failed):
            return ErrorLevel.DESIGN
        return ErrorLevel.CODE

    def _build_summary(self, checks: list[VisualCheck],
                       screenshots: list[ScreenshotResult]) -> str:
        passed = sum(1 for c in checks if c.passed)
        total = len(checks)
        parts = [f"视觉验证: {passed}/{total} 检查通过",
                 f"截图数量: {len(screenshots)}"]
        for c in checks:
            if not c.passed:
                parts.append(f"  X {c.check_name}: {c.detail}")
        return chr(10).join(parts)

    # ── 报告输出 ────────────────────────────────────────────

    def report(self, result: VisualVerificationResult) -> str:
        """生成人类可读的验证报告。"""
        sep = "=" * 50
        parts = [
            sep, "  视觉验证报告", sep,
            f"判定: {result.verdict.value}",
            f"错误等级: {result.error_level.value}",
            f"耗时: {result.elapsed_sec:.2f}s", "",
        ]
        for c in result.checks:
            symbol = "OK" if c.passed else "FAIL"
            parts.append(f"  [{symbol}] {c.check_name}: {c.detail}")
            if not c.passed and c.suggestion:
                parts.append(f"    -> {c.suggestion}")
        if result.screenshots:
            parts.append("")
            parts.append(f"截图 ({len(result.screenshots)} 张):")
            for s in result.screenshots:
                desc = s.description or "(captured)"
                parts.append(f"  - {s.view.value}: {desc}")
        parts.append("")
        parts.append(result.summary)
        return chr(10).join(parts)
    # ── Codex Computer Use 引导 ────────────────────────────

    def generate_codex_guide(self, plan: VisualVerificationPlan) -> str:
        """生成供 Codex Computer Use 执行的 JavaScript 代码片段。"""
        parts: list[str] = []
        parts.append("// FreeCAD Visual Verification - Computer Use Automation")
        parts.append("// Prerequisite: bootstrap complete, sky object available")
        parts.append("")
        parts.append("// Step 1: Find or launch FreeCAD")
        parts.append("const apps = await sky.list_apps();")
        parts.append("let fc = apps.find(a => a.name && a.name.toLowerCase().includes('freecad'));")
        parts.append("if (!fc) {")
        parts.append("  await sky.launch_app({ app: 'FreeCAD' });")
        parts.append("  await new Promise(r => setTimeout(r, 3000));")
        parts.append("  const apps2 = await sky.list_apps();")
        parts.append("  fc = apps2.find(a => a.name && a.name.toLowerCase().includes('freecad'));")
        parts.append("}")
        parts.append("")
        parts.append("// Step 2: Find FreeCAD window")
        parts.append("const fcWindow = await sky.choose_window({")
        parts.append("  titleContains: 'FreeCAD',")
        parts.append("  requireText: 'FreeCAD',")
        parts.append("});")
        parts.append("")
        fpath = plan.fcstd_path
        parts.append(f"// Step 3: Open file {fpath}")
        parts.append("await sky.press_key({ window: fcWindow, key: 'Control_L+o' });")
        parts.append("await new Promise(r => setTimeout(r, 2000));")
        parts.append("")
        parts.append("// Step 4: Wait for load + zoom to fit")
        parts.append("await new Promise(r => setTimeout(r, 2000));")
        parts.append("await sky.press_key({ window: fcWindow, key: 'v' });")
        parts.append("await new Promise(r => setTimeout(r, 300));")
        parts.append("await sky.press_key({ window: fcWindow, key: 'f' });")
        parts.append("await new Promise(r => setTimeout(r, 1000));")
        parts.append("")
        for i, view in enumerate(plan.views):
            shortcut = _VIEW_SHORTCUT_MAP.get(view, "")
            parts.append(f"// Step {5 + i}: Switch to {view.value} view and capture")
            if shortcut:
                parts.append(f"await sky.press_key({{ window: fcWindow, key: '{shortcut}' }});")
            parts.append(f"await new Promise(r => setTimeout(r, {self.viewport_delay_ms}));")
            parts.append(f"const viewState_{i} = await sky.get_window_state({{")
            parts.append("  window: fcWindow,")
            parts.append("  include_screenshot: true,")
            parts.append("});")
            parts.append(f"nodeRepl.write('Screenshot {view.value}: captured');")
            parts.append("")
        if self.include_close:
            parts.append("// Close FreeCAD")
            parts.append("await sky.press_key({ window: fcWindow, key: 'Alt_L+F4' });")
        return chr(10).join(parts)


# ── 便捷函数 ────────────────────────────────────────────────────


def generate_visual_plan(
    fcstd_path: str,
    requirement: RequirementDocument | None = None,
    geometry_review: GeometryReviewReport | None = None,
) -> VisualVerificationPlan:
    """直接生成视觉验证计划。"""
    return VisualVerifier().generate_plan(fcstd_path, requirement, geometry_review)


def analyze_visual(
    screenshots: list[ScreenshotResult],
    requirement: RequirementDocument | None = None,
    geometry_review: GeometryReviewReport | None = None,
    cad_output: CADModelingOutput | None = None,
) -> VisualVerificationResult:
    """直接分析视觉验证结果。"""
    return VisualVerifier().analyze(screenshots, requirement, geometry_review, cad_output)
