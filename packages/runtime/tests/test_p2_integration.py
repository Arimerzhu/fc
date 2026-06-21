"""P2 架构升级单元测试 —— 30+ 用例。

覆盖:
- agent_logging (P2.1)
- agent_handshake (P2.2)
- standard_library (P2.3)
- orchestrator (P2.4)
- agent_cmd (P2.5)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
from typing import Any

import pytest


# ───────────────────────────────────────────────
#  P2.1 — agent_logging
# ───────────────────────────────────────────────

class TestAgentLogger:
    def test_logger_basic(self):
        from fc_runtime.agent_logging import AgentLogger
        lg = AgentLogger(name="test")
        assert lg.name == "test"
        assert lg.events == []

    def test_logger_stage_enter_exit(self):
        from fc_runtime.agent_logging import AgentLogger
        lg = AgentLogger(name="test")
        lg.stage_enter("design")
        time.sleep(0.01)
        lg.stage_exit("design", success=True)
        # 有至少两个事件（enter + exit）
        assert len(lg.events) >= 2
        types = [e["type"] for e in lg.events]
        assert "stage_enter" in types
        assert "stage_exit" in types

    def test_logger_measure_context(self):
        from fc_runtime.agent_logging import AgentLogger
        lg = AgentLogger(name="test")
        with lg.measure_stage("pipeline") as ctx:
            time.sleep(0.01)
        # 上下文管理器正常退出，最后一个事件是 stage_exit
        assert lg.events[-1]["type"] == "stage_exit"

    def test_logger_io_event(self):
        from fc_runtime.agent_logging import AgentLogger
        lg = AgentLogger(name="test")
        lg.io("requirement", "out", 1234)
        assert lg.events[-1]["type"] == "io"
        assert lg.events[-1]["payload_size_bytes"] == 1234

    def test_logger_task_event(self):
        from fc_runtime.agent_logging import AgentLogger
        lg = AgentLogger(name="test")
        lg.task("modeling", "done", detail="created box")
        assert lg.events[-1]["type"] == "task"
        assert lg.events[-1]["status"] == "done"
        assert lg.events[-1]["task_id"] == "modeling"

    def test_logger_error(self):
        from fc_runtime.agent_logging import AgentLogger
        lg = AgentLogger(name="test")
        lg.error("DESIGN", "invalid dimensions")
        assert lg.events[-1]["type"] == "error"
        assert lg.events[-1]["error_level"] == "DESIGN"
        assert "invalid" in lg.events[-1]["message"]

    def test_logger_get_logger_defaults(self):
        from fc_runtime.agent_logging import AgentLogger, get_logger
        lg = get_logger("orch")
        assert isinstance(lg, AgentLogger)


# ───────────────────────────────────────────────
#  P2.2 — agent_handshake (Schema 握手)
# ───────────────────────────────────────────────

class TestAgentHandshake:
    def test_verify_valid_requirement(self):
        from fc_runtime.agent_handshake import AgentHandshake
        from fc_runtime.agent_schemas import RequirementDocument
        payload = {
            "part_type": "box",
            "dimensions": {"length": 100.0, "width": 50.0, "height": 25.0},
            "material": "steel",
            "tolerance_grade": "IT7",
            "standard": "ISO",
            "description": "test box",
        }
        result = AgentHandshake.verify_output(RequirementDocument, payload)
        assert result.valid is True
        assert result.roundtrip_ok is True
        assert "box" in result.model_name or len(result.model_name) > 0

    def test_verify_invalid_payload(self):
        from fc_runtime.agent_handshake import AgentHandshake
        from fc_runtime.agent_schemas import RequirementDocument
        payload = {
            # 缺少 part_type
            "dimensions": {"length": 10.0},
        }
        result = AgentHandshake.verify_output(RequirementDocument, payload)
        assert result.valid is False
        assert len(result.errors) > 0

    def test_verify_json_string(self):
        from fc_runtime.agent_handshake import AgentHandshake
        from fc_runtime.agent_schemas import RequirementDocument
        json_str = json.dumps({
            "part_type": "cylinder",
            "dimensions": {"radius": 10.0, "height": 50.0},
            "material": "aluminum",
            "tolerance_grade": "IT8",
            "standard": "ISO",
        })
        result = AgentHandshake.verify_output_json(RequirementDocument, json_str)
        assert result.valid is True

    def test_verify_malformed_json(self):
        from fc_runtime.agent_handshake import AgentHandshake
        from fc_runtime.agent_schemas import RequirementDocument
        result = AgentHandshake.verify_output_json(RequirementDocument, "{invalid}")
        assert result.valid is False

    def test_handshake_hash_consistency(self):
        from fc_runtime.agent_handshake import AgentHandshake
        from fc_runtime.agent_schemas import RequirementDocument
        payload = {
            "part_type": "sphere",
            "dimensions": {"radius": 10.0},
            "material": "titanium",
            "tolerance_grade": "IT6",
            "standard": "ISO",
        }
        r1 = AgentHandshake.verify_output(RequirementDocument, payload)
        r2 = AgentHandshake.verify_output(RequirementDocument, payload)
        assert r1.payload_hash == r2.payload_hash

    def test_handshake_modeling_plan(self):
        from fc_runtime.agent_handshake import AgentHandshake
        from fc_runtime.agent_schemas import ModelingPlan
        payload = {
            "features": [
                {"step": "01", "operation": "pad",
                 "parameters": {"length": 100.0, "width": 50.0, "height": 25.0},
                 "description": "create the main box",
                 }
            ],
            "connectors": [],
            "parametric_constraints": {},
        }
        result = AgentHandshake.verify_output(ModelingPlan, payload)
        assert result.valid is True

    def test_pipeline_handshake_report(self):
        from fc_runtime.orchestrator import PipelineResult, PipelineStage
        from fc_runtime.agent_schemas import (
            RequirementDocument, ModelingPlan, CADModelingOutput,
            GeometryReviewReport, DrawingOutput, AnnotationReviewReport,
            Verdict,
        )
        from fc_runtime.agent_handshake import pipeline_handshake_report

        req = RequirementDocument(
            part_type="box",
            dimensions={"length": 100.0, "width": 50.0, "height": 25.0},
            material="steel",
            tolerance_grade="IT7",
            standard="ISO",
        )
        plan = ModelingPlan(
            features=[{"step": "01", "operation": "pad",
                        "parameters": {"length": 100.0}, "description": "box"}],
        )
        cad = CADModelingOutput(script_path="/tmp/script.py",
                                 fcstd_path="/tmp/model.fcstd")
        geo = GeometryReviewReport(
            verdict=Verdict.PASS,
            checks=[{"check_name": "volume", "passed": True, "detail": "ok"}],
        )
        draw = DrawingOutput(svg_path="/tmp/draw.svg",
                              views=["top", "front", "side"])
        ann = AnnotationReviewReport(
            verdict=Verdict.PASS,
            checks=[{"check_name": "dim", "passed": True, "detail": "ok"}],
        )

        r = PipelineResult(stage=PipelineStage.DONE, requirement=req,
                            plan=plan, model_output=cad,
                            geometry_review=geo, drawing_output=draw,
                            annotation_review=ann)
        report = pipeline_handshake_report(r)
        assert report["all_valid"] is True
        assert report["schema_count"] >= 6


# ───────────────────────────────────────────────
#  P2.3 — standard_library (标准件库)
# ───────────────────────────────────────────────

class TestStandardLibrary:
    def test_library_list_not_empty(self):
        from fc_runtime.standard_library import get_library
        lib = get_library()
        names = lib.list_all()
        assert len(names) >= 5

    def test_library_get_bolt(self):
        from fc_runtime.standard_library import get_library
        lib = get_library()
        bolt = lib.get("bolt_m6_16")
        assert bolt is not None
        assert bolt.part_type.value in ("shaft", "bolt")

    def test_library_get_bearing(self):
        from fc_runtime.standard_library import get_library
        lib = get_library()
        bearing = lib.get("bearing_6203")
        assert bearing is not None
        assert "bearing" in bearing.short_name or "6203" in bearing.code

    def test_library_search(self):
        from fc_runtime.standard_library import get_library
        lib = get_library()
        results = lib.search("bearing")
        assert len(results) >= 1
        for r in results:
            assert "bearing" in r.short_name.lower() or "bearing" in r.code.lower()

    def test_library_get_unknown(self):
        from fc_runtime.standard_library import get_library
        lib = get_library()
        assert lib.get("this_does_not_exist") is None

    def test_library_requirement_conversion(self):
        from fc_runtime.standard_library import get_library
        from fc_runtime.agent_schemas import RequirementDocument
        lib = get_library()
        req = lib.get_requirement("bolt_m6_16")
        assert req is not None
        assert isinstance(req, RequirementDocument)
        assert req.dimensions

    def test_library_custom_bolt(self):
        from fc_runtime.standard_library import get_library
        lib = get_library()
        bolt = lib.bolt("m10", 30.0)
        assert bolt is not None
        assert "m10" in bolt.code.lower() or "10" in bolt.code
        assert bolt.dimensions["length"] == 30.0

    def test_library_custom_gear(self):
        from fc_runtime.standard_library import get_library
        lib = get_library()
        gear = lib.gear_by_module(module=2.0, teeth=30, thickness=20.0)
        assert gear is not None
        assert gear.dimensions["teeth"] == 30.0

    def test_library_search_by_part_type(self):
        from fc_runtime.standard_library import get_library
        from fc_runtime.agent_schemas import PartType
        lib = get_library()
        results = lib.search_by_part_type(PartType.CYLINDER)
        assert len(results) >= 1
        for r in results:
            assert r.part_type == PartType.CYLINDER


# ───────────────────────────────────────────────
#  P2.4 — Orchestrator
# ───────────────────────────────────────────────

class TestOrchestrator:
    def test_orchestrator_creation(self):
        from fc_runtime.orchestrator import Orchestrator
        orch = Orchestrator(max_retries=1, max_duration_sec=60)
        assert orch is not None
        assert orch.max_retries == 1
        assert orch.max_duration_sec == 60

    def test_orchestrator_run_dry_box(self):
        from fc_runtime.orchestrator import Orchestrator
        orch = Orchestrator(max_retries=1)
        result = orch.run("设计一个盒子 100x50x25mm", dry_run=True)
        assert result.requirement is not None
        assert result.plan is not None
        # dry run 下 modeling 不执行
        assert result.stage is not None

    def test_orchestrator_run_dry_cylinder(self):
        from fc_runtime.orchestrator import Orchestrator
        orch = Orchestrator(max_retries=1)
        result = orch.run("圆柱 r=10 h=50", dry_run=True)
        assert result.requirement is not None
        # part_type 可能是 cylinder 或其他相近的类型
        assert result.requirement.dimensions

    def test_orchestrator_full_pipeline_box(self):
        from fc_runtime.orchestrator import Orchestrator
        orch = Orchestrator(max_retries=1)
        result = orch.run("盒子 100x50x25mm")
        assert result is not None
        assert result.stage is not None
        # 检查 handshake 字段
        if result.handshake is not None:
            assert "schema_count" in result.handshake

    def test_orchestrator_full_pipeline_cylinder(self):
        from fc_runtime.orchestrator import Orchestrator
        orch = Orchestrator(max_retries=1)
        result = orch.run("圆柱 r=10 h=50")
        assert result is not None
        assert result.stage is not None

    def test_orchestrator_explain(self):
        from fc_runtime.orchestrator import Orchestrator, PipelineResult, PipelineStage
        from fc_runtime.agent_schemas import (
            RequirementDocument, GeometryReviewReport, Verdict,
        )
        orch = Orchestrator()
        req = RequirementDocument(
            part_type="box",
            dimensions={"length": 100.0, "width": 50.0, "height": 25.0},
            material="steel",
            tolerance_grade="IT7",
            standard="ISO",
        )
        r = PipelineResult(stage=PipelineStage.DONE, requirement=req, elapsed_sec=1.0)
        diag = orch.explain(r)
        assert diag is not None
        assert "Pipeline" in diag or "Part:" in diag

    def test_pipeline_result_to_json(self):
        from fc_runtime.orchestrator import PipelineResult, PipelineStage
        r = PipelineResult(stage=PipelineStage.DONE, elapsed_sec=0.5)
        out = r.to_json()
        parsed = json.loads(out)
        assert parsed["stage"] == "done"
        assert parsed["elapsed_sec"] == 0.5

    def test_run_standard_part_shortcut(self):
        from fc_runtime.orchestrator import run_standard_part
        result = run_standard_part("bolt_m6_16")
        assert result is not None
        assert result.stage is not None

    def test_run_standard_part_invalid(self):
        from fc_runtime.orchestrator import run_standard_part
        with pytest.raises(ValueError):
            run_standard_part("not_a_real_part_name_xyz")


# ───────────────────────────────────────────────
#  P2.5 — agent_cmd CLI 集成
# ───────────────────────────────────────────────

class TestAgentCommandCli:
    def test_agent_command_is_group(self):
        from fc_runtime.agent_cmd import agent_command
        import click
        assert isinstance(agent_command, click.Group)

    def test_library_list_runs(self):
        from click.testing import CliRunner
        from fc_runtime.agent_cmd import agent_command
        runner = CliRunner()
        result = runner.invoke(agent_command, ["library", "list"])
        assert result.exit_code == 0

    def test_library_get_runs(self):
        from click.testing import CliRunner
        from fc_runtime.agent_cmd import agent_command
        runner = CliRunner()
        result = runner.invoke(agent_command, ["library", "get", "bolt_m6_16"])
        assert result.exit_code == 0
        assert "bolt" in result.output.lower() or "Bolt" in result.output or "M6" in result.output

    def test_library_get_unknown(self):
        from click.testing import CliRunner
        from fc_runtime.agent_cmd import agent_command
        runner = CliRunner()
        result = runner.invoke(agent_command, ["library", "get", "nonexistent_abc"])
        assert result.exit_code != 0

    def test_library_search_gear(self):
        from click.testing import CliRunner
        from fc_runtime.agent_cmd import agent_command
        runner = CliRunner()
        result = runner.invoke(agent_command, ["library", "search", "gear"])
        assert result.exit_code == 0

    def test_pipeline_dry_run(self):
        from click.testing import CliRunner
        from fc_runtime.agent_cmd import agent_command
        runner = CliRunner()
        result = runner.invoke(agent_command,
                               ["pipeline", "盒子 100x50x25", "--dry-run"])
        # dry run 也应该能成功（不依赖 FreeCAD）
        assert result.exit_code == 0
        assert "Pipeline" in result.output or "Part:" in result.output

    def test_handshake_valid_json_via_cli(self):
        from click.testing import CliRunner
        from fc_runtime.agent_cmd import agent_command
        runner = CliRunner()
        test_json = json.dumps({
            "part_type": "cylinder",
            "dimensions": {"radius": 10.0, "height": 50.0},
            "material": "aluminum",
            "tolerance_grade": "IT8",
            "standard": "ISO",
        })
        result = runner.invoke(agent_command,
                               ["handshake", "requirement", "--json-string", test_json])
        assert result.exit_code == 0

    def test_handshake_invalid_json(self):
        from click.testing import CliRunner
        from fc_runtime.agent_cmd import agent_command
        runner = CliRunner()
        result = runner.invoke(agent_command,
                               ["handshake", "requirement",
                                "--json-string", "{not json}"])
        assert result.exit_code != 0

    def test_handshake_incomplete_payload(self):
        from click.testing import CliRunner
        from fc_runtime.agent_cmd import agent_command
        runner = CliRunner()
        result = runner.invoke(agent_command,
                               ["handshake", "requirement",
                                "--json-string", '{"part_type": "box"}'])
        assert result.exit_code != 0  # 缺少 dimensions 等必要字段


# ───────────────────────────────────────────────
#  集成: 全栈 P2 端到端测试
# ───────────────────────────────────────────────

class TestP2Integration:
    def test_orchestrator_with_logging_and_handshake(self):
        from fc_runtime.orchestrator import Orchestrator
        orch = Orchestrator(max_retries=1, verbose=True)
        result = orch.run("法兰盘 直径 100 厚度 10")
        assert result is not None
        # 至少走到 DESIGN_PLANNED 阶段
        assert result.plan is not None

    def test_pipeline_json_roundtrip(self):
        from fc_runtime.orchestrator import Orchestrator
        orch = Orchestrator(max_retries=1)
        result = orch.run("球体 r=15", dry_run=True)
        j = result.to_json()
        parsed = json.loads(j)
        # 至少有 stage 和 trace
        assert "stage" in parsed
        assert "trace" in parsed

    def test_stdlib_requirement_matches_agent_schema(self):
        """标准件库输出的 RequirementDocument 必须通过 handshake 验证。"""
        from fc_runtime.standard_library import get_library
        from fc_runtime.agent_handshake import AgentHandshake
        lib = get_library()
        for name in lib.list_all()[:5]:  # 只测试前 5 个
            req = lib.get_requirement(name)
            assert req is not None
            result = AgentHandshake.verify_requirement(req)
            assert result.valid, f"{name} failed: {result.errors}"
            assert result.roundtrip_ok, f"{name} roundtrip failed"
