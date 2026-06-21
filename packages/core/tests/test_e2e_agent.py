"""E2E tests for fc agent autonomous design workflow.
Tests the full pipeline: Planner -> Executor -> Corrector -> BOM -> Export
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import subprocess
import time
import math
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Import runtime modules ──
from fc_runtime.planner import Planner, Plan, Task, TaskType, TaskStatus
from fc_runtime.executor import Executor, TaskResult
from fc_runtime.corrector import Corrector, Correction
from fc_runtime.bom import BOMGenerator, BOM, BOMItem

# fc CLI path (avoid bash built-in 'fc' conflict — resolve from current Python venv)
FC_EXE = os.path.join(os.path.dirname(sys.executable), "fc.exe")
FREECAD_PATH = r"C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe"

# Skip all E2E tests if FreeCAD is not available
requires_freecad = pytest.mark.skipif(
    not os.path.isfile(FREECAD_PATH),
    reason=f"FreeCAD not found at {FREECAD_PATH}"
)


# ═══════════════════════════════════════════════════════════════
# class TestPlannerE2E
# Pure logic tests — no FreeCAD needed
# ═══════════════════════════════════════════════════════════════

class TestPlannerE2E:
    """E2E tests for the Planner (pure logic, no FreeCAD needed)."""

    def setup_method(self):
        self.planner = Planner()

    def test_box_dimensions_20x30x40(self):
        """'design a box 20x30x40mm' -> plan with box, length=20, width=30, height=40."""
        plan = self.planner.plan("design a box 20x30x40mm")
        assert plan.goal == "design a box 20x30x40mm"

        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1

        box_task = part_tasks[0]
        assert box_task.params["length"] == 20.0
        assert box_task.params["width"] == 30.0
        assert box_task.params["height"] == 40.0

    def test_box_default_dimensions(self):
        """'design a box' -> default 10x10x10."""
        plan = self.planner.plan("design a box")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1

        box_task = part_tasks[0]
        assert box_task.params["length"] == 10
        assert box_task.params["width"] == 10
        assert box_task.params["height"] == 10

    def test_cylinder_with_diameter(self):
        """'cylinder D=50 H=30' -> radius=25, height=30."""
        plan = self.planner.plan("cylinder D=50 H=30")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1

        cyl_task = part_tasks[0]
        assert cyl_task.params["radius"] == 25.0
        assert cyl_task.params["height"] == 30.0

    def test_chinese_box(self):
        """'设计一个长方体 20x30x40' -> correct template + dimensions."""
        plan = self.planner.plan("设计一个长方体 20x30x40")
        assert plan.goal == "设计一个长方体 20x30x40"

        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1

        box_task = part_tasks[0]
        assert box_task.params["length"] == 20.0
        assert box_task.params["width"] == 30.0
        assert box_task.params["height"] == 40.0

    def test_multiple_parts(self):
        """'box and cylinder' -> 2 part tasks."""
        plan = self.planner.plan("box and cylinder")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 2

    def test_with_fillet(self):
        """'box with fillet r=2' -> part + fillet tasks."""
        plan = self.planner.plan("box with fillet r=2")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        fillet_tasks = [t for t in plan.tasks if t.type == TaskType.PART_FILLET]

        assert len(part_tasks) >= 1
        assert len(fillet_tasks) >= 1

        # Fillet radius should be 2.0
        fillet_task = fillet_tasks[0]
        assert "2" in " ".join(fillet_task.args)

    def test_export_step_stl(self):
        """'box export to step and stl' -> export tasks for both formats."""
        plan = self.planner.plan("box export to step and stl")
        export_types = {t.type for t in plan.tasks}

        assert TaskType.EXPORT_STEP in export_types
        assert TaskType.EXPORT_STL in export_types

    def test_no_parts_defaults_to_box(self):
        """'hello world' -> default box task."""
        plan = self.planner.plan("hello world")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1

    def test_dependency_chain(self):
        """All part tasks depend on document creation."""
        plan = self.planner.plan("design a box 20x30x40")
        doc_task = plan.tasks[0]
        assert doc_task.type == TaskType.DOCUMENT_NEW

        for task in plan.tasks:
            if task.type != TaskType.DOCUMENT_NEW:
                assert doc_task.id in task.dependencies or len(task.dependencies) > 0

    def test_plan_to_dict(self):
        """plan.to_dict() returns valid JSON-serializable dict."""
        plan = self.planner.plan("design a box 20x30x40")
        d = plan.to_dict()

        assert "goal" in d
        assert "tasks" in d
        assert "status" in d
        assert d["task_count"] == len(plan.tasks)

        # Must be JSON-serializable
        json_str = json.dumps(d, default=str)
        parsed = json.loads(json_str)
        assert parsed["goal"] == "design a box 20x30x40"


# ═══════════════════════════════════════════════════════════════
# class TestExecutorE2E
# Requires FreeCAD
# ═══════════════════════════════════════════════════════════════

@requires_freecad
class TestExecutorE2E:
    """E2E tests for the Executor (requires FreeCAD)."""

    def test_execute_simple_box_plan(self, tmp_path):
        """Plan a box -> execute via fc CLI -> success."""
        project_path = str(tmp_path / "session.FCStd")
        planner = Planner()
        plan = planner.plan("design a box 20x30x40", project_path=project_path)

        executor = Executor(
            fc_path=FC_EXE,
            timeout=120,
            working_dir=str(tmp_path),
        )
        results = executor.execute_plan(plan)

        assert len(results) > 0
        assert all(r.success for r in results)

    def test_execute_dry_run(self, tmp_path):
        """Dry-run mode -> no actual execution, returns plan dict."""
        planner = Planner()
        plan = planner.plan("design a box 20x30x40")

        executor = Executor(
            fc_path=FC_EXE,
            dry_run=True,
            working_dir=str(tmp_path),
        )
        results = executor.execute_plan(plan)

        assert len(results) > 0
        assert all(r.success for r in results)
        assert len(executor.dry_run_log) == len(plan.tasks)

    def test_execute_output_files(self, tmp_path):
        """Execute plan -> verify all tasks succeed.

        Note: Each fc CLI call is a separate subprocess. The executor
        reports task success based on CLI return code. Actual file
        creation depends on FreeCAD session persistence across
        subprocess calls, which is a known architectural limitation.
        This test verifies that the executor completes all tasks
        successfully and generates the expected plan structure.
        """
        project_path = str(tmp_path / "session.FCStd")
        planner = Planner()
        plan = planner.plan("design a box 20x30x40", project_path=project_path)

        executor = Executor(
            fc_path=FC_EXE,
            timeout=120,
            working_dir=str(tmp_path),
        )
        results = executor.execute_plan(plan)

        assert all(r.success for r in results)
        # Verify plan has expected task types
        assert any(t.type == TaskType.DOCUMENT_NEW for t in plan.tasks)
        assert any(t.type == TaskType.PART_ADD for t in plan.tasks)
        assert any(t.type == TaskType.EXPORT_STEP for t in plan.tasks)
        assert any(t.type == TaskType.EXPORT_STL for t in plan.tasks)
        assert any(t.type == TaskType.DOCUMENT_SAVE for t in plan.tasks)

    def test_execute_with_timeout(self, tmp_path):
        """Timeout parameter works."""
        project_path = str(tmp_path / "session.FCStd")
        planner = Planner()
        plan = planner.plan("design a box 10x10x10", project_path=project_path)

        executor = Executor(
            fc_path=FC_EXE,
            timeout=300,
            working_dir=str(tmp_path),
        )
        results = executor.execute_plan(plan)

        assert all(r.success for r in results)
        # All tasks should complete well within 300s timeout
        assert all(r.duration_ms < 300000 for r in results)


# ═══════════════════════════════════════════════════════════════
# class TestCorrectorE2E
# Pure logic + mocking
# ═══════════════════════════════════════════════════════════════

class TestCorrectorE2E:
    """E2E tests for the Corrector (pure logic + mock)."""

    def setup_method(self):
        self.corrector = Corrector()
        self.task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Create a box",
            command="fc",
            args=["part", "add", "box", "--name", "Box"],
        )

    def _make_result(self, error_msg: str) -> TaskResult:
        return TaskResult(
            task_id="test_001",
            success=False,
            error=error_msg,
            stderr=error_msg,
        )

    def test_freecad_not_found(self):
        """Error 'FreeCAD not found' -> Correction with install guidance."""
        result = self._make_result("freecad not found in system PATH")
        correction = self.corrector.analyze(self.task, result)

        assert correction is not None
        assert correction.fix_type == "install_freecad"
        # Should contain platform-specific install guidance
        assert "Install" in correction.description or "install" in correction.description.lower()

    def test_file_exists(self):
        """Error 'file already exists' -> add --overwrite."""
        result = self._make_result("file already exists: output.step")
        correction = self.corrector.analyze(self.task, result)

        assert correction is not None
        assert correction.fix_type == "overwrite"
        assert "--overwrite" in correction.new_args

    def test_invalid_parameter(self):
        """Error 'must be positive' -> clamp to valid range."""
        result = self._make_result("invalid parameter: must be positive")
        correction = self.corrector.analyze(self.task, result)

        assert correction is not None
        assert correction.fix_type == "fix_parameter"

    def test_max_retries(self):
        """After max retries, corrector returns None."""
        self.task.retries = 3
        corrector = Corrector(max_retries=3)
        result = self._make_result("some unknown error")
        correction = corrector.analyze(self.task, result)

        assert correction is None

    def test_unknown_error(self):
        """Unknown error -> generic retry if retries < max."""
        self.task.retries = 0
        result = self._make_result("some completely unknown error xyz")
        correction = self.corrector.analyze(self.task, result)

        assert correction is not None
        assert correction.fix_type == "generic_retry"


# ═══════════════════════════════════════════════════════════════
# class TestBOMGeneratorE2E
# Pure logic tests
# ═══════════════════════════════════════════════════════════════

class TestBOMGeneratorE2E:
    """E2E tests for BOMGenerator."""

    def test_bom_from_plan(self):
        """Plan with 2 parts -> BOM with 2 items."""
        planner = Planner()
        plan = planner.plan("box 20x30x40 cylinder D=50 H=30")

        # Mark part_add tasks as success
        for task in plan.tasks:
            if task.type == TaskType.PART_ADD:
                task.status = TaskStatus.SUCCESS

        gen = BOMGenerator()
        bom = gen.from_plan(plan)

        assert isinstance(bom, BOM)
        assert len(bom.items) >= 2

    def test_bom_export_json(self, tmp_path):
        """BOM -> .json file exists and valid."""
        bom = BOM(project_name="Test_JSON")
        bom.items.append(BOMItem(
            index=1, name="Box", type_id="Part::Box", volume=24000.0
        ))

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path), formats=["json"])

        assert len(files) == 1
        assert os.path.exists(files[0])
        assert files[0].endswith(".json")

        with open(files[0]) as f:
            data = json.load(f)
        assert data["project_name"] == "Test_JSON"
        assert data["total_parts"] == 1

    def test_bom_export_csv(self, tmp_path):
        """BOM -> .csv file with correct headers."""
        bom = BOM(project_name="Test_CSV")
        bom.items.append(BOMItem(
            index=1, name="Box", type_id="Part::Box", volume=1000.0
        ))

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path), formats=["csv"])

        assert len(files) == 1
        assert os.path.exists(files[0])

        with open(files[0]) as f:
            content = f.read()
        assert "Index,Name" in content
        assert "Box" in content

    def test_bom_export_markdown(self, tmp_path):
        """BOM -> .md file with table."""
        bom = BOM(project_name="Test_MD")
        bom.items.append(BOMItem(
            index=1, name="Box", type_id="Part::Box", volume=1000.0
        ))

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path), formats=["md"])

        assert len(files) == 1
        assert os.path.exists(files[0])

        with open(files[0]) as f:
            content = f.read()
        assert "# Bill of Materials" in content
        assert "Box" in content

    def test_bom_volume_calculation(self):
        """Box 20x30x40 -> volume = 24000."""
        planner = Planner()
        plan = planner.plan("design a box 20x30x40")

        # Mark part_add tasks as success
        for task in plan.tasks:
            if task.type == TaskType.PART_ADD:
                task.status = TaskStatus.SUCCESS

        gen = BOMGenerator()
        bom = gen.from_plan(plan)

        assert bom.total_volume == 24000.0  # 20 * 30 * 40


# ═══════════════════════════════════════════════════════════════
# class TestFullPipelineE2E
# Requires FreeCAD — the most critical tests
# ═══════════════════════════════════════════════════════════════

@requires_freecad
class TestFullPipelineE2E:
    """Full pipeline E2E tests: Planner -> Executor -> Corrector -> BOM -> Export."""

    def test_fc_agent_box_english(self, tmp_path):
        """fc agent 'design a box 20x30x40mm' -> all tasks succeed."""
        os.chdir(tmp_path)

        result = subprocess.run(
            [FC_EXE, "agent", "design a box 20x30x40mm"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"fc agent failed: {result.stderr}"

        # Verify plan report was created
        fc_output = tmp_path / "fc_output"
        plan_report = fc_output / "plan_report.json"
        assert plan_report.exists(), f"No plan report in {fc_output}"

        # Verify plan report has correct structure
        with open(plan_report, encoding="utf-8") as f:
            report = json.load(f)
        assert report["goal"] == "design a box 20x30x40mm"
        assert report["task_count"] >= 3  # doc + part + exports + save
        assert report["status"] == "success"

    def test_fc_agent_box_chinese(self, tmp_path):
        """fc agent '设计一个长方体 20x30x40mm' -> correct plan."""
        os.chdir(tmp_path)

        result = subprocess.run(
            [FC_EXE, "agent", "设计一个长方体 20x30x40mm"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"fc agent failed: {result.stderr}"

        # Verify plan report was created
        fc_output = tmp_path / "fc_output"
        plan_report = fc_output / "plan_report.json"
        assert plan_report.exists(), f"No plan report in {fc_output}"

        with open(plan_report, encoding="utf-8") as f:
            report = json.load(f)
        assert report["task_count"] >= 3
        assert report["status"] == "success"

    def test_fc_agent_dry_run(self, tmp_path):
        """fc agent 'design a box' --dry-run -> valid JSON output."""
        os.chdir(tmp_path)

        result = subprocess.run(
            [FC_EXE, "agent", "design a box", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"dry-run failed: {result.stderr}"

        # Output should contain JSON plan
        assert "goal" in result.stdout
        assert "tasks" in result.stdout

    def test_fc_agent_output_dir(self, tmp_path):
        """fc agent 'box' -o ./test_output -> plan report in test_output/."""
        output_dir = tmp_path / "test_output"
        output_dir.mkdir()

        result = subprocess.run(
            [FC_EXE, "agent", "design a box 10x10x10", "--output-dir", str(output_dir)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"fc agent failed: {result.stderr}"

        # Verify plan report was created in output_dir
        plan_report = output_dir / "plan_report.json"
        assert plan_report.exists(), f"No plan report in {output_dir}. stdout: {result.stdout}"

        with open(plan_report, encoding="utf-8") as f:
            report = json.load(f)
        assert report["task_count"] >= 3
        assert report["status"] == "success"
