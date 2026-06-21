"""Visual Verifier 单元测试 — 覆盖视觉验证核心模块 + 集成层。

目标: >= 40 个测试用例。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


# == VisualVerifier 基础 ==

class TestVisualVerifierBasics:
    def test_default_views(self):
        from fc_runtime.visual_verifier import VisualVerifier, ViewAngle
        vv = VisualVerifier()
        assert len(vv.views) == 4
        assert ViewAngle.ISOMETRIC in vv.views
        assert ViewAngle.FRONT in vv.views

    def test_custom_views(self):
        from fc_runtime.visual_verifier import VisualVerifier, ViewAngle
        vv = VisualVerifier(views=[ViewAngle.TOP, ViewAngle.BOTTOM])
        assert len(vv.views) == 2
        assert ViewAngle.TOP in vv.views

    def test_include_close_default(self):
        from fc_runtime.visual_verifier import VisualVerifier
        vv = VisualVerifier()
        assert vv.include_close is True

    def test_include_close_false(self):
        from fc_runtime.visual_verifier import VisualVerifier
        vv = VisualVerifier(include_close=False)
        assert vv.include_close is False

    def test_viewport_delay_default(self):
        from fc_runtime.visual_verifier import VisualVerifier
        vv = VisualVerifier()
        assert vv.viewport_delay_ms == 2000

    def test_viewport_delay_custom(self):
        from fc_runtime.visual_verifier import VisualVerifier
        vv = VisualVerifier(viewport_delay_ms=5000)
        assert vv.viewport_delay_ms == 5000


# == Plan 生成 ==

class TestPlanGeneration:
    def test_generate_plan_no_requirement(self):
        from fc_runtime.visual_verifier import VisualVerifier, ActionType
        vv = VisualVerifier()
        plan = vv.generate_plan(fcstd_path="/tmp/test.FCStd")
        assert plan.fcstd_path == "/tmp/test.FCStd"
        assert len(plan.actions) > 0
        assert plan.part_type == "unknown"

    def test_generate_plan_with_requirement(self):
        from fc_runtime.visual_verifier import VisualVerifier
        from fc_runtime.agent_schemas import RequirementDocument, PartType
        vv = VisualVerifier()
        req = RequirementDocument(
            part_type=PartType.BOX,
            dimensions={"length": 100.0, "width": 50.0, "height": 30.0},
        )
        plan = vv.generate_plan(fcstd_path="/tmp/box.FCStd", requirement=req)
        assert plan.part_type == "box"
        assert plan.expected_properties["part_type"] == "box"

    def test_plan_has_launch_action(self):
        from fc_runtime.visual_verifier import VisualVerifier, ActionType
        vv = VisualVerifier()
        plan = vv.generate_plan(fcstd_path="/tmp/test.FCStd")
        launch_actions = [a for a in plan.actions if a.action_type == ActionType.LAUNCH_APP]
        assert len(launch_actions) == 1

    def test_plan_has_capture_actions(self):
        from fc_runtime.visual_verifier import VisualVerifier, ActionType
        vv = VisualVerifier()
        plan = vv.generate_plan(fcstd_path="/tmp/test.FCStd")
        captures = [a for a in plan.actions if a.action_type == ActionType.CAPTURE_SCREENSHOT]
        assert len(captures) >= 4
        assert plan.screenshot_count == len(captures)

    def test_plan_with_close(self):
        from fc_runtime.visual_verifier import VisualVerifier, ActionType
        vv = VisualVerifier(include_close=True)
        plan = vv.generate_plan(fcstd_path="/tmp/test.FCStd")
        close_actions = [a for a in plan.actions if a.action_type == ActionType.CLOSE_APP]
        assert len(close_actions) == 1

    def test_plan_without_close(self):
        from fc_runtime.visual_verifier import VisualVerifier, ActionType
        vv = VisualVerifier(include_close=False)
        plan = vv.generate_plan(fcstd_path="/tmp/test.FCStd")
        close_actions = [a for a in plan.actions if a.action_type == ActionType.CLOSE_APP]
        assert len(close_actions) == 0

    def test_plan_action_count(self):
        from fc_runtime.visual_verifier import VisualVerifier
        vv = VisualVerifier()
        plan = vv.generate_plan(fcstd_path="/tmp/test.FCStd")
        # launch + wait + find + open + wait + zoom + wait + 4*(set_view + wait + capture) + close
        # = 1 + 1 + 1 + 1 + 1 + 1 + 1 + 4*3 + 1 = 20
        assert len(plan.actions) == 20

    def test_plan_json_serialization(self):
        from fc_runtime.visual_verifier import VisualVerifier
        vv = VisualVerifier()
        plan = vv.generate_plan(fcstd_path="/tmp/test.FCStd")
        json_str = plan.to_json()
        data = json.loads(json_str)
        assert "fcstd_path" in data
        assert "views" in data
        assert "actions" in data
        assert len(data["actions"]) == 20


# == View Inference ==

class TestViewInference:
    def test_plate_views(self):
        from fc_runtime.visual_verifier import _infer_expected_views, ViewAngle
        views = _infer_expected_views("plate", {"length": 100, "width": 80, "height": 5})
        assert ViewAngle.ISOMETRIC in views
        assert ViewAngle.TOP in views

    def test_shaft_views(self):
        from fc_runtime.visual_verifier import _infer_expected_views, ViewAngle
        views = _infer_expected_views("shaft", {"diameter": 20, "length": 200})
        assert ViewAngle.ISOMETRIC in views
        assert ViewAngle.FRONT in views

    def test_sphere_views(self):
        from fc_runtime.visual_verifier import _infer_expected_views, ViewAngle
        views = _infer_expected_views("sphere", {"diameter": 50})
        assert len(views) == 2
        assert ViewAngle.ISOMETRIC in views

    def test_unknown_type_views(self):
        from fc_runtime.visual_verifier import _infer_expected_views
        views = _infer_expected_views("custom", {"length": 100, "width": 50, "height": 30})
        assert len(views) == 4


# == Aspect Ratio ==

class TestAspectRatio:
    def test_flat_ratio(self):
        from fc_runtime.visual_verifier import _estimate_aspect_ratio
        result = _estimate_aspect_ratio("plate", {"length": 100, "width": 80, "height": 5})
        assert result == "flat"

    def test_elongated_ratio(self):
        from fc_runtime.visual_verifier import _estimate_aspect_ratio
        result = _estimate_aspect_ratio("shaft", {"length": 200, "width": 20, "height": 20})
        assert result == "elongated"

    def test_cubic_ratio(self):
        from fc_runtime.visual_verifier import _estimate_aspect_ratio
        result = _estimate_aspect_ratio("box", {"length": 100, "width": 95, "height": 100})
        assert result == "cubic"

    def test_irregular_ratio(self):
        from fc_runtime.visual_verifier import _estimate_aspect_ratio
        result = _estimate_aspect_ratio("custom", {"length": 100, "width": 50, "height": 30})
        assert result == "irregular"


# == Analysis ==

class TestAnalyze:
    def test_analyze_no_data(self):
        from fc_runtime.visual_verifier import VisualVerifier, Verdict
        vv = VisualVerifier()
        result = vv.analyze(screenshots=[])
        assert result.verdict == Verdict.PASS
        assert len(result.checks) > 0

    def test_analyze_with_passing_geometry(self):
        from fc_runtime.visual_verifier import VisualVerifier, Verdict
        from fc_runtime.agent_schemas import (
            RequirementDocument, PartType, GeometryReviewReport,
            GeometryCheck, Verdict as SchemaVerdict, ErrorLevel,
        )
        geo = GeometryReviewReport(
            verdict=SchemaVerdict.PASS,
            checks=[GeometryCheck(check_name="face_count", passed=True, detail="OK")],
            error_level=ErrorLevel.NONE,
        )
        req = RequirementDocument(
            part_type=PartType.BOX,
            dimensions={"length": 100, "width": 50, "height": 30},
        )
        vv = VisualVerifier()
        result = vv.analyze([], requirement=req, geometry_review=geo)
        assert result.verdict == Verdict.PASS

    def test_analyze_with_failing_geometry(self):
        from fc_runtime.visual_verifier import VisualVerifier, Verdict
        from fc_runtime.agent_schemas import (
            RequirementDocument, PartType, GeometryReviewReport,
            GeometryCheck, Verdict as SchemaVerdict, ErrorLevel,
        )
        geo = GeometryReviewReport(
            verdict=SchemaVerdict.FAIL,
            checks=[GeometryCheck(check_name="volume", passed=False, detail="vol=0")],
            error_level=ErrorLevel.DESIGN,
        )
        req = RequirementDocument(
            part_type=PartType.BOX,
            dimensions={"length": 100, "width": 50, "height": 30},
        )
        vv = VisualVerifier()
        result = vv.analyze([], requirement=req, geometry_review=geo)
        assert result.verdict == Verdict.FAIL

    def test_analyze_aspect_ratio_mismatch(self):
        from fc_runtime.visual_verifier import VisualVerifier
        from fc_runtime.agent_schemas import RequirementDocument, PartType
        req = RequirementDocument(
            part_type=PartType.SHAFT,
            dimensions={"length": 200, "width": 20, "height": 2},
        )
        vv = VisualVerifier()
        result = vv.analyze([], requirement=req)
        # shaft with dimensions that make it look flat -> check behavior
        ar_check = [c for c in result.checks if c.check_name == "aspect_ratio"]
        assert len(ar_check) == 1
        # shaft with very low height relative to length/width -> flat mismatch
        assert "flat" in ar_check[0].detail

    def test_analyze_bounding_box_zero(self):
        from fc_runtime.visual_verifier import VisualVerifier
        from fc_runtime.agent_schemas import (
            RequirementDocument, PartType, CADModelingOutput,
        )
        req = RequirementDocument(
            part_type=PartType.BOX,
            dimensions={"length": 100, "width": 50, "height": 30},
        )
        cad = CADModelingOutput(
            script_path="/tmp/s.py", fcstd_path="/tmp/m.fcstd",
            bounding_box=(0.0, 0.0, 0.0),
        )
        vv = VisualVerifier()
        result = vv.analyze([], requirement=req, cad_output=cad)
        bb_check = [c for c in result.checks if c.check_name == "bounding_box_reasonable"]
        assert len(bb_check) == 1
        assert bb_check[0].passed is False

    def test_analyze_visual_inspection_check_present(self):
        from fc_runtime.visual_verifier import VisualVerifier, ScreenshotResult, ViewAngle
        vv = VisualVerifier()
        screenshots = [ScreenshotResult(view=ViewAngle.ISOMETRIC)]
        result = vv.analyze(screenshots)
        vi_check = [c for c in result.checks if c.check_name == "visual_inspection_needed"]
        assert len(vi_check) == 1
        assert vi_check[0].passed is True

    def test_error_level_none_when_all_pass(self):
        from fc_runtime.visual_verifier import VisualVerifier, Verdict
        from fc_runtime.agent_schemas import ErrorLevel
        vv = VisualVerifier()
        result = vv.analyze([])
        assert result.error_level == ErrorLevel.NONE


# == Report ==

class TestReport:
    def test_report_contains_verdict(self):
        from fc_runtime.visual_verifier import VisualVerifier
        vv = VisualVerifier()
        result = vv.analyze([])
        report = vv.report(result)
        assert "PASS" in report or "FAIL" in report

    def test_report_contains_check_names(self):
        from fc_runtime.visual_verifier import VisualVerifier
        vv = VisualVerifier()
        result = vv.analyze([])
        report = vv.report(result)
        assert "dimension_consistency" in report

    def test_report_includes_screenshots(self):
        from fc_runtime.visual_verifier import (
            VisualVerifier, ScreenshotResult, ViewAngle,
        )
        vv = VisualVerifier()
        screenshots = [
            ScreenshotResult(view=ViewAngle.ISOMETRIC, description="iso view"),
            ScreenshotResult(view=ViewAngle.FRONT, description="front view"),
        ]
        result = vv.analyze(screenshots)
        report = vv.report(result)
        assert "isometric" in report
        assert "front" in report


# == Codex Guide ==

class TestCodexGuide:
    def test_guide_contains_sky_api(self):
        from fc_runtime.visual_verifier import VisualVerifier
        vv = VisualVerifier()
        plan = vv.generate_plan(fcstd_path="/tmp/test.FCStd")
        guide = vv.generate_codex_guide(plan)
        assert "sky." in guide

    def test_guide_contains_view_steps(self):
        from fc_runtime.visual_verifier import VisualVerifier
        vv = VisualVerifier()
        plan = vv.generate_plan(fcstd_path="/tmp/test.FCStd")
        guide = vv.generate_codex_guide(plan)
        assert "isometric" in guide
        assert "front" in guide

    def test_guide_contains_close(self):
        from fc_runtime.visual_verifier import VisualVerifier
        vv = VisualVerifier(include_close=True)
        plan = vv.generate_plan(fcstd_path="/tmp/test.FCStd")
        guide = vv.generate_codex_guide(plan)
        assert "Alt_L+F4" in guide


# == Integration ==

class TestIntegration:
    def test_verify_pipeline_result_no_model(self):
        from fc_runtime.visual_verification import verify_pipeline_result
        from fc_runtime.orchestrator import PipelineResult, PipelineStage
        pr = PipelineResult(stage=PipelineStage.DONE)
        result = verify_pipeline_result(pr)
        assert result.pipeline_passed is True
        assert result.visual_plan is None

    def test_verify_pipeline_result_failed(self):
        from fc_runtime.visual_verification import verify_pipeline_result
        from fc_runtime.orchestrator import PipelineResult, PipelineStage
        from fc_runtime.agent_schemas import ErrorLevel
        pr = PipelineResult(stage=PipelineStage.FAILED)
        pr.errors.append((ErrorLevel.CODE, "test error"))
        result = verify_pipeline_result(pr)
        assert result.pipeline_passed is False

    def test_bridge_orchestrator_to_visual(self):
        from fc_runtime.visual_verification import bridge_orchestrator_to_visual
        result = bridge_orchestrator_to_visual("一个铁盒子 100x50x30mm")
        assert result.pipeline_passed is True
        assert result.visual_plan is not None

    def test_generate_codex_visual_script(self):
        from fc_runtime.visual_verification import generate_codex_visual_script
        from fc_runtime.orchestrator import Orchestrator
        orch = Orchestrator()
        pr = orch.run("一个铁盒子 100x50x30mm")
        script = generate_codex_visual_script(pr)
        # May be None if no FCStd file
        # But should not crash
        assert script is None or "sky." in script

    def test_integrated_result_to_json(self):
        from fc_runtime.visual_verification import bridge_orchestrator_to_visual
        result = bridge_orchestrator_to_visual("一个铁盒子 100x50x30mm")
        json_str = result.to_json()
        data = json.loads(json_str)
        assert "pipeline_stage" in data
        assert "overall_verdict" in data

    def test_max_error_level(self):
        from fc_runtime.visual_verification import _max_error_level
        from fc_runtime.agent_schemas import ErrorLevel
        assert _max_error_level([ErrorLevel.NONE, ErrorLevel.CODE]) == ErrorLevel.CODE
        assert _max_error_level([ErrorLevel.CODE, ErrorLevel.DESIGN]) == ErrorLevel.DESIGN
        assert _max_error_level([ErrorLevel.NONE]) == ErrorLevel.NONE
        assert _max_error_level([]) == ErrorLevel.NONE


# == Module Imports ==

class TestModuleImports:
    def test_import_visual_verifier(self):
        from fc_runtime.visual_verifier import VisualVerifier
        assert VisualVerifier is not None

    def test_import_view_angle(self):
        from fc_runtime.visual_verifier import ViewAngle
        assert len(ViewAngle) == 7

    def test_import_action_type(self):
        from fc_runtime.visual_verifier import ActionType
        assert len(ActionType) == 9

    def test_import_convenience_functions(self):
        from fc_runtime.visual_verifier import generate_visual_plan, analyze_visual
        assert callable(generate_visual_plan)
        assert callable(analyze_visual)

    def test_import_integration(self):
        from fc_runtime.visual_verification import (
            verify_pipeline_result, bridge_orchestrator_to_visual,
            IntegratedVerificationResult,
        )
        assert callable(verify_pipeline_result)
        assert callable(bridge_orchestrator_to_visual)

    def test_orchestrator_has_visual_fields(self):
        from fc_runtime.orchestrator import PipelineResult, PipelineStage
        pr = PipelineResult(stage=PipelineStage.NEW)
        assert hasattr(pr, "visual_plan_json")
        assert hasattr(pr, "visual_result_data")

    def test_pipeline_stage_has_visual_review(self):
        from fc_runtime.orchestrator import PipelineStage
        assert hasattr(PipelineStage, "VISUAL_REVIEW")
        assert PipelineStage.VISUAL_REVIEW.value == "visual_review"
