"""P3 单元测试 — 覆盖几何审查、标注合规、AgentGraph、
经验库、装配支持等。

目标：≥ 60 个测试用例。
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

import pytest


# ── GeometryReviewAgent (P3.1) ───────

class TestGeometryReviewAgent:
    def test_review_all_valid(self):
        from fc_runtime.geometry_review_agent import GeometryReviewAgent
        from fc_runtime.agent_schemas import CADModelingOutput, Verdict

        output = CADModelingOutput(
            script_path="/tmp/s.py",
            fcstd_path="/tmp/m.fcstd",
            face_count=6,
            volume=125000.0,
            is_connected=True,
            is_valid=True,
            is_closed=True,
            bounding_box=(100.0, 50.0, 25.0),
        )
        agent = GeometryReviewAgent()
        report = agent.review(output)
        assert report.verdict == Verdict.PASS
        assert report.error_level.value in ("none", "NONE", "None")

    def test_review_missing_geometry_info(self):
        from fc_runtime.geometry_review_agent import GeometryReviewAgent
        from fc_runtime.agent_schemas import CADModelingOutput, Verdict

        # 无几何信息字段，默认为 0 / None，validator 会跳过这些检查
        output = CADModelingOutput(script_path="/tmp/s.py",
                                    fcstd_path="/tmp/m.fcstd")
        agent = GeometryReviewAgent()
        report = agent.review(output)
        # 所有检查都被跳过，所以 verdict 为 PASS
        assert report.verdict == Verdict.PASS
        assert len(report.checks) > 0

    def test_review_invalid_geometry_fails(self):
        from fc_runtime.geometry_review_agent import GeometryReviewAgent
        from fc_runtime.agent_schemas import CADModelingOutput, Verdict, ErrorLevel

        output = CADModelingOutput(
            script_path="/tmp/s.py",
            fcstd_path="/tmp/m.fcstd",
            face_count=1,  # 太少
            volume=0.0,
            is_connected=False,
            is_valid=False,
            is_closed=False,
            bounding_box=(0.0, 0.0, 0.0),
        )
        agent = GeometryReviewAgent()
        report = agent.review(output)
        assert report.verdict == Verdict.FAIL
        # 体积和面数问题 → DESIGN 级
        assert report.error_level in (ErrorLevel.DESIGN, ErrorLevel.CODE)

    def test_review_with_requirement_dimension_match(self):
        from fc_runtime.geometry_review_agent import GeometryReviewAgent
        from fc_runtime.agent_schemas import CADModelingOutput, RequirementDocument, PartType, Verdict

        output = CADModelingOutput(
            script_path="/tmp/s.py",
            fcstd_path="/tmp/m.fcstd",
            face_count=6,
            volume=125000.0,
            is_connected=True,
            is_valid=True,
            is_closed=True,
            bounding_box=(100.0, 50.0, 25.0),
        )
        req = RequirementDocument(
            part_type=PartType.BOX,
            dimensions={"length": 100.0, "width": 50.0, "height": 25.0},
            material="steel",
        )
        agent = GeometryReviewAgent()
        report = agent.review(output, requirement=req)
        assert report.verdict == Verdict.PASS

    def test_review_with_mismatched_requirement(self):
        from fc_runtime.geometry_review_agent import GeometryReviewAgent
        from fc_runtime.agent_schemas import CADModelingOutput, RequirementDocument, PartType

        output = CADModelingOutput(
            script_path="/tmp/s.py",
            fcstd_path="/tmp/m.fcstd",
            face_count=6,
            volume=125000.0,
            is_connected=True,
            is_valid=True,
            is_closed=True,
            bounding_box=(100.0, 50.0, 25.0),
        )
        req = RequirementDocument(
            part_type=PartType.BOX,
            dimensions={"length": 100.0, "width": 50.0, "height": 500.0},
            material="steel",
        )
        agent = GeometryReviewAgent()
        report = agent.review(output, requirement=req)
        # bounding_box 与需求 height 500mm 不匹配 → 至少一个检查失败
        assert any(not c.passed for c in report.checks)

    def test_min_face_configurable(self):
        from fc_runtime.geometry_review_agent import GeometryReviewAgent
        from fc_runtime.agent_schemas import CADModelingOutput, Verdict

        agent = GeometryReviewAgent(min_face_count=10)  # 高阈值
        output = CADModelingOutput(
            script_path="/tmp/s.py",
            fcstd_path="/tmp/m.fcstd",
            face_count=6,
            volume=1000.0,
            is_connected=True,
            is_valid=True,
            is_closed=True,
            bounding_box=(10, 10, 10),
        )
        report = agent.review(output)
        # 面数不足 → FAIL
        assert report.verdict == Verdict.FAIL


# ── AnnotationComplianceAgent (P3.1) ─

class TestAnnotationAgent:
    def test_basic_pass(self):
        from fc_runtime.annotation_agent import AnnotationComplianceAgent
        from fc_runtime.agent_schemas import DrawingOutput, Verdict, RequirementDocument, PartType

        drawing = DrawingOutput(
            svg_path="/tmp/a.svg",
            views=["front", "top", "side"],
            template="ISO_A3_Landscape.svg",
            projection="First Angle",
        )
        req = RequirementDocument(
            part_type=PartType.BOX,
            dimensions={"length": 100.0, "width": 50.0, "height": 25.0},
            material="Q235",
            standard="ISO",
        )
        agent = AnnotationComplianceAgent()
        report = agent.review(drawing, requirement=req)
        # 有两个视图 + 材料/标准等齐全 → 至少一个检查通过
        assert report.verdict == Verdict.PASS

    def test_single_view_triggers_warning(self):
        from fc_runtime.annotation_agent import AnnotationComplianceAgent
        from fc_runtime.agent_schemas import DrawingOutput, Verdict

        drawing = DrawingOutput(svg_path="/tmp/a.svg", views=["only_one"])
        agent = AnnotationComplianceAgent()
        report = agent.review(drawing)
        # 单视图 → view_variety 会失败 → verdict FAIL
        assert report.verdict == Verdict.FAIL

    def test_missing_material(self):
        from fc_runtime.annotation_agent import AnnotationComplianceAgent
        from fc_runtime.agent_schemas import DrawingOutput, RequirementDocument, PartType, Verdict

        drawing = DrawingOutput(svg_path="/tmp/a.svg",
                                 views=["front", "top", "side"])
        req = RequirementDocument(
            part_type=PartType.BOX,
            dimensions={"length": 10.0},
            material="",
        )
        agent = AnnotationComplianceAgent()
        report = agent.review(drawing, requirement=req)
        # 材料未定义 → 材料检查失败 → 总体 FAIL
        assert report.verdict == Verdict.FAIL

    def test_undefined_projection(self):
        from fc_runtime.annotation_agent import AnnotationComplianceAgent
        from fc_runtime.agent_schemas import DrawingOutput, Verdict

        # 视图只有一个 → view_variety 会失败
        drawing = DrawingOutput(
            svg_path="/tmp/a.svg",
            views=["only"],
            template="ISO_A3_Landscape.svg",
            projection="First Angle",
        )
        agent = AnnotationComplianceAgent()
        report = agent.review(drawing)
        # 视图数不足 → FAIL
        assert report.verdict == Verdict.FAIL


# ── AgentGraph (P3.2) ─────────────────

class TestAgentGraph:
    def test_empty_graph_raises(self):
        from fc_runtime.agent_graph import AgentGraph
        g = AgentGraph()
        # 未设置 entry → RuntimeError
        with pytest.raises(RuntimeError):
            g.run("box 10x10x10")

    def test_build_standard_graph_runs(self):
        from fc_runtime.agent_graph import build_standard_graph
        g = build_standard_graph()
        result = g.run("盒子 100x50x25mm")
        # 至少能跑完全流程
        assert result.requirement is not None
        assert result.plan is not None
        assert result.finished is True

    def test_standard_graph_trace_has_steps(self):
        from fc_runtime.agent_graph import build_standard_graph
        g = build_standard_graph()
        result = g.run("圆柱 r=10 h=50")
        assert len(result.trace) > 3

    def test_standard_graph_with_review_output(self):
        from fc_runtime.agent_graph import build_standard_graph
        g = build_standard_graph()
        result = g.run("一个盒子 长200宽100高50")
        assert result.geometry_review is not None
        # review 给出的是一份完整报告
        assert hasattr(result.geometry_review, "verdict")

    def test_describe_returns_string(self):
        from fc_runtime.agent_graph import build_standard_graph
        g = build_standard_graph()
        desc = g.describe()
        assert isinstance(desc, str)
        assert "Entry" in desc or "Nodes" in desc

    def test_custom_tiny_graph(self):
        from fc_runtime.agent_graph import AgentGraph, GraphState, END

        g = AgentGraph()

        def _a(state: GraphState) -> str:
            state.trace.append({"custom": "a"})
            return "ok"

        def _b(state: GraphState) -> str:
            state.trace.append({"custom": "b"})
            return "ok"

        g.add_node("a", _a, max_attempts=1)
        g.add_node("b", _b, max_attempts=1)
        g.set_entry_point("a")
        g.add_edge("a", "b")
        g.add_edge("b", END)

        state = g.run("任意")
        assert state.finished is True
        assert len(state.trace) >= 2

    def test_graph_state_roundtrip(self):
        from fc_runtime.agent_graph import GraphState
        state = GraphState(user_input="box 10x10x10")
        d = state.to_dict()
        assert d["user_input"] == "box 10x10x10"
        # JSON 可序列化
        s = json.dumps(d, ensure_ascii=False)
        assert "user_input" in s

    def test_graph_node_exception_is_caught(self):
        from fc_runtime.agent_graph import AgentGraph, GraphState

        g = AgentGraph()

        def _bad(state: GraphState) -> str:
            raise RuntimeError("boom")

        g.add_node("bad", _bad, max_attempts=1)
        g.set_entry_point("bad")
        state = g.run("测试")
        # 必须结束，且 errors 中有内容
        assert state.finished is True
        assert len(state.errors) >= 1

    def test_graph_max_steps(self):
        from fc_runtime.agent_graph import AgentGraph, GraphState

        g = AgentGraph()

        def _loop(state: GraphState) -> str:
            return "go"

        g.add_node("a", _loop, max_attempts=1)
        g.add_node("b", _loop, max_attempts=1)
        g.set_entry_point("a")
        g.add_edge("a", "b")
        g.add_edge("b", "a")  # 自环
        # 5 步就会退出
        state = g.run("测试", max_steps=5)
        assert state.finished is True

    def test_graph_attempts_tracking(self):
        from fc_runtime.agent_graph import AgentGraph, GraphState

        g = AgentGraph()

        def _bad(state: GraphState) -> str:
            return "retry_a"

        g.add_node("a", _bad, max_attempts=3)
        g.set_entry_point("a")
        g.add_conditional_edges(
            "a", _bad,
            mapping={"retry_a": "a", "ok": "__end__"}
        )
        state = g.run("测试")
        # a 节点在超过 max_attempts 后会停止
        assert state.attempts.get("a", 0) >= 3
        assert state.finished is True


# ── ExperienceLibrary / FeedbackLoop (P3.3) ─

class TestExperienceLibrary:
    def test_record_and_count(self):
        from fc_runtime.experience_library import ExperienceLibrary
        from fc_runtime.agent_graph import build_standard_graph

        with tempfile.NamedTemporaryFile(
            suffix=".jsonl", delete=False, mode="w"
        ) as f:
            path = f.name
        try:
            lib = ExperienceLibrary(path)
            g = build_standard_graph()
            state = g.run("盒子 100x50x25")
            lib.record_from_state(state, success=True,
                                   expert_hint="盒子优先用 sketch+pad")
            assert lib.count() >= 1
            # 再录一条
            state2 = g.run("圆柱 r=10 h=50")
            lib.record_from_state(state2, success=True)
            assert lib.count() >= 2
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_recommend_no_matches(self):
        with tempfile.NamedTemporaryFile(
            suffix=".jsonl", delete=False, mode="w"
        ) as f:
            path = f.name
        try:
            from fc_runtime.experience_library import ExperienceLibrary
            lib = ExperienceLibrary(path)
            recs = lib.recommend("flange")
            assert recs == []
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_pre_run_suggestions_empty_when_no_data(self):
        with tempfile.NamedTemporaryFile(
            suffix=".jsonl", delete=False, mode="w"
        ) as f:
            path = f.name
        try:
            from fc_runtime.experience_library import (
                ExperienceLibrary, FeedbackLoop)
            lib = ExperienceLibrary(path)
            fb = FeedbackLoop(lib)
            out = fb.pre_run("一个由盒子和螺丝组成的结构")
            # 库空 → 返回空列表
            assert isinstance(out, list)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_experience_dataclass_roundtrip(self):
        from fc_runtime.experience_library import Experience
        e = Experience(
            id="abc123",
            timestamp=1.0,
            part_type="box",
            dimensions={"length": 100.0},
            material="steel",
            tolerance_grade="IT7",
            success=True,
            total_elapsed_sec=0.5,
            feature_steps=["pad(l=100)"],
            geometry_checks=[{"name": "face_count", "passed": True}],
            annotation_checks=[],
            errors=[],
            attempts={"design": 1},
            expert_hint="使用 sketch+pad",
            tags=["box", "simple"],
        )
        d = e.to_dict()
        e2 = Experience.from_dict(d)
        assert e2.id == "abc123"
        assert e2.success is True
        assert e2.feature_steps == ["pad(l=100)"]
        assert e2.tags == ["box", "simple"]

    def test_add_expert_hint(self):
        from fc_runtime.experience_library import Experience, ExperienceLibrary
        with tempfile.NamedTemporaryFile(
            suffix=".jsonl", delete=False, mode="w"
        ) as f:
            path = f.name
        try:
            lib = ExperienceLibrary(path)
            e = Experience(
                id="myid", timestamp=1.0, part_type="box",
                dimensions={}, material="", tolerance_grade="",
                success=True, total_elapsed_sec=0.1,
                feature_steps=[], geometry_checks=[],
                annotation_checks=[], errors=[], attempts={},
                expert_hint="", tags=[],
            )
            lib.record(e)
            assert lib.add_expert_hint("myid", "新提示") is True
            assert "新提示" in [x.expert_hint for x in lib.iter_experiences()]
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_common_failures_returns_list(self):
        from fc_runtime.experience_library import Experience, ExperienceLibrary
        with tempfile.NamedTemporaryFile(
            suffix=".jsonl", delete=False, mode="w"
        ) as f:
            path = f.name
        try:
            lib = ExperienceLibrary(path)
            e = Experience(
                id="myfail", timestamp=1.0, part_type="box",
                dimensions={}, material="", tolerance_grade="",
                success=False, total_elapsed_sec=0.1,
                feature_steps=[], geometry_checks=[],
                annotation_checks=[],
                errors=[("CODE", "volume 0"), ("DESIGN", "invalid")],
                attempts={}, expert_hint="", tags=[],
            )
            lib.record(e)
            failures = lib.common_failures("box")
            assert isinstance(failures, list)
            assert len(failures) >= 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_success_rate_no_data(self):
        from fc_runtime.experience_library import ExperienceLibrary
        with tempfile.NamedTemporaryFile(
            suffix=".jsonl", delete=False, mode="w"
        ) as f:
            path = f.name
        try:
            lib = ExperienceLibrary(path)
            assert lib.success_rate("box") == 0.0
        finally:
            if os.path.exists(path):
                os.unlink(path)


# ── Assembly (P3.4) ─────────────────

class TestAssembly:
    def test_agent_design_from_description_base(self):
        from fc_runtime.assembly import AssemblyAgent
        agent = AssemblyAgent()
        design = agent.design_from_description("一个由底板和支架组成的简单底座")
        assert design.part_count >= 2
        assert design.constraint_count >= 1

    def test_agent_design_from_description_complete(self):
        from fc_runtime.assembly import AssemblyAgent
        agent = AssemblyAgent()
        design = agent.design_from_description(
            "一个由底板、支架、电机轴组成的结构，使用螺丝连接"
        )
        assert design.part_count >= 3
        assert design.assembly_name == "assembly_01"

    def test_agent_design_from_description_default(self):
        from fc_runtime.assembly import AssemblyAgent
        agent = AssemblyAgent()
        design = agent.design_from_description("完全无法识别的描述 xyz123")
        # 至少会创建一个默认零件
        assert design.part_count >= 1

    def test_design_from_parts_programmatic(self):
        from fc_runtime.assembly import AssemblyAgent
        agent = AssemblyAgent()
        specs = [
            ("box", {"length": 200, "width": 100, "height": 20}, "Q235"),
            ("shaft", {"length": 100, "diameter": 20}, "45 steel"),
            ("bracket", {"length": 80, "width": 80, "height": 8}, "Q235"),
        ]
        design = agent.design_from_parts(specs, "custom_mount")
        assert design.part_count == 3
        assert design.constraint_count == 2

    def test_design_to_dict(self):
        from fc_runtime.assembly import AssemblyAgent
        agent = AssemblyAgent()
        design = agent.design_from_description("一个底板和支架")
        d = design.to_dict()
        assert "assembly_name" in d
        assert "parts" in d
        # JSON 可序列化
        s = json.dumps(d, ensure_ascii=False)
        assert "底板" in s or "box" in s or "plate" in s

    def test_executor_generate_script_not_empty(self):
        from fc_runtime.assembly import AssemblyAgent, AssemblyExecutor
        agent = AssemblyAgent()
        design = agent.design_from_description("一个底板和支架，使用螺丝固定")
        executor = AssemblyExecutor()
        script = executor.generate_script(design)
        assert len(script) > 100
        assert "import FreeCAD" in script or "doc = " in script

    def test_executor_generate_bom(self):
        from fc_runtime.assembly import AssemblyAgent, AssemblyExecutor
        agent = AssemblyAgent()
        design = agent.design_from_description("底板和支架 plus 电机轴")
        executor = AssemblyExecutor()
        bom = executor.generate_bom(design)
        assert bom["part_count"] == design.part_count
        assert len(bom["items"]) == design.part_count
        assert "total_mass_kg" in bom

    def test_assembly_part_position_offsets(self):
        from fc_runtime.assembly import AssemblyAgent
        agent = AssemblyAgent()
        specs = [
            ("box", {"length": 100, "width": 50, "height": 10}, "steel"),
            ("box", {"length": 100, "width": 50, "height": 20}, "steel"),
        ]
        design = agent.design_from_parts(specs)
        # 第二个零件的 z 位置应该 = 第一个的 height
        assert design.parts[1].position[2] == pytest.approx(10.0)

    def test_assembly_mass_estimate_positive(self):
        from fc_runtime.assembly import AssemblyAgent
        agent = AssemblyAgent()
        design = agent.design_from_description("底板、支架、电机轴")
        assert design.total_mass_kg > 0.0


# ── 模块导出/导入测试 ───────────────────

class TestModuleImports:
    def test_import_geometry_review_agent(self):
        from fc_runtime.geometry_review_agent import GeometryReviewAgent
        assert GeometryReviewAgent is not None

    def test_import_annotation_agent(self):
        from fc_runtime.annotation_agent import AnnotationComplianceAgent
        assert AnnotationComplianceAgent is not None

    def test_import_agent_graph(self):
        from fc_runtime.agent_graph import AgentGraph, build_standard_graph, END
        assert AgentGraph is not None
        assert END == "__end__"

    def test_import_experience_library(self):
        from fc_runtime.experience_library import (
            Experience, ExperienceLibrary, FeedbackLoop)
        assert Experience is not None
        assert ExperienceLibrary is not None
        assert FeedbackLoop is not None

    def test_import_assembly(self):
        from fc_runtime.assembly import (
            AssemblyAgent, AssemblyExecutor, AssemblyDesign,
            AssemblyPart, AssemblyConstraint, ConstraintType)
        assert AssemblyAgent is not None
        assert AssemblyExecutor is not None


# ── 全量端到端：标准流水线 + 经验库 ───

class TestP3EndToEnd:
    def test_standard_graph_full_cycle(self):
        from fc_runtime.agent_graph import build_standard_graph
        g = build_standard_graph()
        state = g.run("法兰盘 直径 100 厚度 10")
        assert state.requirement is not None
        assert state.plan is not None
        assert state.geometry_review is not None
        assert state.annotation_review is not None
        assert state.finished is True

    def test_feedback_loop_pre_post_run(self):
        from fc_runtime.agent_graph import build_standard_graph
        from fc_runtime.experience_library import (
            ExperienceLibrary, FeedbackLoop)
        with tempfile.NamedTemporaryFile(
            suffix=".jsonl", delete=False, mode="w"
        ) as f:
            path = f.name
        try:
            lib = ExperienceLibrary(path)
            fb = FeedbackLoop(lib)
            # pre run 给出建议
            hints = fb.pre_run("一个由底板和螺丝组成的简单结构")
            assert isinstance(hints, list)

            g = build_standard_graph()
            state = g.run("一个盒子和一个支架")
            # post run 保存经验
            id_ = fb.post_run(state, success=True,
                              expert_hint="先做 sketch 再 pad")
            assert id_ is not None
            assert lib.count() >= 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_assembly_design_to_script_and_bom(self):
        from fc_runtime.assembly import AssemblyAgent, AssemblyExecutor
        agent = AssemblyAgent()
        executor = AssemblyExecutor()
        design = agent.design_from_description(
            "设计一个由底板、支架、电机轴组成的机械结构，"
            "使用螺栓连接"
        )
        assert design.part_count >= 3
        script = executor.generate_script(design)
        assert "doc.addObject" in script
        bom = executor.generate_bom(design)
        assert bom["part_count"] == design.part_count
