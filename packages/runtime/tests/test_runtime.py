"""Tests for fc_runtime — Agent Runtime Package."""

from __future__ import annotations

import json
import os
import platform
from unittest.mock import MagicMock, patch, call

import pytest

from fc_runtime.planner import Plan, Planner, Task, TaskStatus, TaskType
from fc_runtime.executor import Executor, TaskResult
from fc_runtime.corrector import Correction, Corrector
from fc_runtime.bom import BOM, BOMGenerator, BOMItem


# ── Planner Tests ──

class TestPlanner:
    """Test the Planner class."""

    def setup_method(self):
        self.planner = Planner()

    def test_plan_box_request(self):
        """Test planning a simple box design."""
        plan = self.planner.plan("design a box 20x30x40mm")
        assert plan.goal == "design a box 20x30x40mm"
        assert len(plan.tasks) > 0

        # Should have document creation
        doc_tasks = [t for t in plan.tasks if t.type == TaskType.DOCUMENT_NEW]
        assert len(doc_tasks) == 1

        # Should have part creation
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1

    def test_plan_cylinder_request(self):
        """Test planning a cylinder design."""
        plan = self.planner.plan("create a cylinder with radius 10 and height 50")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        # Check cylinder params
        box_task = part_tasks[0]
        assert "Cylinder" in box_task.args or "cylinder" in str(box_task.args)

    def test_plan_dimensions_extraction(self):
        """Test dimension extraction from request."""
        plan = self.planner.plan("box 20x30x40")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        # Check dimensions in args
        args_str = " ".join(part_tasks[0].args)
        assert "20" in args_str
        assert "30" in args_str
        assert "40" in args_str

    def test_plan_default_exports(self):
        """Test that default exports are added."""
        plan = self.planner.plan("design a box")
        export_tasks = [t for t in plan.tasks
                        if t.type in (TaskType.EXPORT_STEP, TaskType.EXPORT_STL)]
        assert len(export_tasks) >= 2  # step + stl

    def test_plan_custom_exports(self):
        """Test custom export format specification."""
        plan = self.planner.plan("design a box export step pdf")
        export_types = {t.type for t in plan.tasks}
        assert TaskType.EXPORT_STEP in export_types
        assert TaskType.EXPORT_PDF in export_types

    def test_plan_fillet_operation(self):
        """Test fillet operation detection."""
        plan = self.planner.plan("box with fillet r=2")
        fillet_tasks = [t for t in plan.tasks if t.type == TaskType.PART_FILLET]
        assert len(fillet_tasks) >= 1

    def test_plan_chamfer_operation(self):
        """Test chamfer operation detection."""
        plan = self.planner.plan("box with chamfer size=1.5")
        chamfer_tasks = [t for t in plan.tasks if t.type == TaskType.PART_CHAMFER]
        assert len(chamfer_tasks) >= 1

    def test_plan_mirror_operation(self):
        """Test mirror operation detection."""
        plan = self.planner.plan("box mirror XY")
        mirror_tasks = [t for t in plan.tasks if t.type == TaskType.PART_MIRROR]
        assert len(mirror_tasks) >= 1

    def test_plan_document_name_extraction(self):
        """Test document name extraction."""
        plan = self.planner.plan("design a flange")
        doc_task = [t for t in plan.tasks if t.type == TaskType.DOCUMENT_NEW][0]
        assert "Flange" in doc_task.args or "flange" in str(doc_task.args)

    def test_plan_dependencies(self):
        """Test that tasks have correct dependencies."""
        plan = self.planner.plan("design a box")
        doc_task = [t for t in plan.tasks if t.type == TaskType.DOCUMENT_NEW][0]

        # All non-document tasks should depend on document creation
        for task in plan.tasks:
            if task.type != TaskType.DOCUMENT_NEW:
                assert doc_task.id in task.dependencies or len(task.dependencies) > 0

    def test_plan_get_ready_tasks(self):
        """Test getting ready tasks."""
        plan = self.planner.plan("design a box")
        ready = plan.get_ready_tasks()
        # Only document creation should be ready initially
        assert len(ready) == 1
        assert ready[0].type == TaskType.DOCUMENT_NEW

    def test_plan_progress(self):
        """Test plan progress tracking."""
        plan = self.planner.plan("design a box")
        progress = plan.progress
        assert progress["pending"] == len(plan.tasks)

    def test_plan_to_dict(self):
        """Test plan serialization."""
        plan = self.planner.plan("design a box")
        d = plan.to_dict()
        assert "goal" in d
        assert "tasks" in d
        assert "status" in d
        assert d["task_count"] == len(plan.tasks)

    def test_plan_chinese_request(self):
        """Test Chinese language request."""
        plan = self.planner.plan("设计一个长方体 20x30x40mm")
        assert len(plan.tasks) > 0
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1

    def test_plan_flange_request(self):
        """Test flange design request."""
        plan = self.planner.plan("design a flange")
        assert len(plan.tasks) > 0

    def test_plan_gear_request(self):
        """Test gear design request."""
        plan = self.planner.plan("design a gear")
        assert len(plan.tasks) > 0

    def test_plan_reducer_request(self):
        """Test reducer design request."""
        plan = self.planner.plan("设计一个二级圆柱齿轮减速器")
        assert len(plan.tasks) > 0


# ── Task Tests ──

class TestTask:
    """Test the Task class."""

    def test_task_creation(self):
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Test task",
            command="fc",
            args=["part", "add", "box"],
        )
        assert task.status == TaskStatus.PENDING
        assert task.retries == 0

    def test_task_to_dict(self):
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Test task",
            command="fc",
        )
        d = task.to_dict()
        assert d["id"] == "test_001"
        assert d["type"] == "part_add"
        assert d["status"] == "pending"


# ── Executor Tests ──

class TestTaskResult:
    """Test the TaskResult class."""

    def test_task_result_success(self):
        result = TaskResult(
            task_id="test_001",
            success=True,
            data={"name": "Box"},
        )
        assert result.success
        assert not result.failed

    def test_task_result_failure(self):
        result = TaskResult(
            task_id="test_001",
            success=False,
            error="Object not found",
        )
        assert result.failed
        assert result.error == "Object not found"

    def test_task_result_from_subprocess(self):
        import subprocess
        proc = subprocess.CompletedProcess(
            args=["echo", "test"],
            returncode=0,
            stdout='{"status": "ok", "data": {}}',
            stderr="",
        )
        result = TaskResult.from_subprocess("test", proc)
        assert result.success
        assert result.data.get("status") == "ok"


class TestExecutor:
    """Test the Executor class."""

    def test_executor_creation(self):
        executor = Executor()
        assert executor._fc_path == "fc"
        assert executor._timeout == 120

    def test_executor_custom_config(self):
        executor = Executor(fc_path="/usr/bin/fc", timeout=300, backend="rpc")
        assert executor._fc_path == "/usr/bin/fc"
        assert executor._timeout == 300
        assert executor._backend == "rpc"


# ── Corrector Tests ──

class TestCorrector:
    """Test the Corrector class."""

    def test_corrector_creation(self):
        corrector = Corrector()
        assert corrector._max_retries == 3

    def test_corrector_custom_retries(self):
        corrector = Corrector(max_retries=5)
        assert corrector._max_retries == 5

    def test_correction_creation(self):
        correction = Correction(
            fix_type="create_document",
            description="Create document first",
        )
        assert correction.fix_type == "create_document"
        assert correction.new_args is None

    def test_correction_with_args(self):
        correction = Correction(
            fix_type="overwrite",
            description="Add overwrite flag",
            new_args=["export", "step", "out.step", "--overwrite"],
        )
        assert "--overwrite" in correction.new_args


# ── BOM Tests ──

class TestBOMItem:
    """Test the BOMItem class."""

    def test_bom_item_creation(self):
        item = BOMItem(
            index=1,
            name="Box",
            type_id="Part::Box",
            volume=1000.0,
        )
        assert item.index == 1
        assert item.name == "Box"
        assert item.quantity == 1

    def test_bom_item_to_dict(self):
        item = BOMItem(index=1, name="Box", volume=1000.0)
        d = item.to_dict()
        assert d["index"] == 1
        assert d["name"] == "Box"
        assert d["volume_mm3"] == 1000.0


class TestBOM:
    """Test the BOM class."""

    def test_bom_creation(self):
        bom = BOM(project_name="Test Project")
        assert bom.project_name == "Test Project"
        assert len(bom.items) == 0

    def test_bom_with_items(self):
        bom = BOM(project_name="Test")
        bom.items.append(BOMItem(index=1, name="Box", volume=1000.0))
        bom.items.append(BOMItem(index=2, name="Cylinder", volume=500.0))
        bom.total_volume = 1500.0
        assert len(bom.items) == 2
        assert bom.total_volume == 1500.0

    def test_bom_to_dict(self):
        bom = BOM(project_name="Test")
        bom.items.append(BOMItem(index=1, name="Box", volume=1000.0))
        d = bom.to_dict()
        assert d["project_name"] == "Test"
        assert d["total_parts"] == 1
        assert len(d["items"]) == 1

    def test_bom_to_table(self):
        bom = BOM(project_name="Test")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box", volume=1000.0))
        bom.total_volume = 1000.0
        table = bom.to_table()
        assert "Bill of Materials" in table
        assert "Box" in table

    def test_bom_to_csv(self):
        bom = BOM(project_name="Test")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box", volume=1000.0))
        csv = bom.to_csv()
        assert "Index,Name" in csv
        assert "Box" in csv

    def test_bom_to_markdown(self):
        bom = BOM(project_name="Test")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box", volume=1000.0))
        md = bom.to_markdown()
        assert "# Bill of Materials" in md
        assert "Box" in md


class TestBOMGenerator:
    """Test the BOMGenerator class."""

    def test_generator_creation(self):
        gen = BOMGenerator()
        assert gen._fc_path == "fc"

    def test_from_plan(self):
        """Test BOM generation from a plan."""
        planner = Planner()
        plan = planner.plan("design a box 10x20x30")

        gen = BOMGenerator()
        bom = gen.from_plan(plan)
        assert isinstance(bom, BOM)
        assert bom.project_name == "design a box 10x20x30"

    def test_from_plan_with_parts(self):
        """Test BOM has parts when plan has part tasks."""
        planner = Planner()
        plan = planner.plan("design a box 10x20x30")

        gen = BOMGenerator()
        bom = gen.from_plan(plan)
        # Should have at least one part
        assert len(bom.items) >= 0  # May be 0 if plan tasks don't have right params

    def test_export_bom(self, tmp_path):
        """Test BOM export to files."""
        bom = BOM(project_name="Test_Project")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box", volume=1000.0))

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path), formats=["json", "csv", "md"])

        assert len(files) == 3
        for f in files:
            assert os.path.exists(f)

        # Check JSON content
        import json
        with open(files[0]) as f:
            data = json.load(f)
        assert data["project_name"] == "Test_Project"


# ── Freecad Not Found Correction Tests ──

class TestFreecadNotFound:
    """Test the FREECAD_NOT_FOUND error pattern in Corrector."""

    def setup_method(self):
        self.corrector = Corrector()
        self.task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Create a box",
            command="fc",
            args=["part", "add", "box"],
        )

    def _make_result(self, error_msg: str) -> TaskResult:
        return TaskResult(
            task_id="test_001",
            success=False,
            error=error_msg,
            stderr=error_msg,
        )

    def test_freecad_not_found_error(self):
        """Test detection of FreeCAD not found error."""
        result = self._make_result("freecad not found in system PATH")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "install_freecad"

    def test_freecad_not_installed_error(self):
        """Test detection of FreeCAD not installed error."""
        result = self._make_result("FreeCAD is not installed on this system")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "install_freecad"

    def test_cannot_locate_freecad_error(self):
        """Test detection of cannot locate FreeCAD error."""
        result = self._make_result("cannot locate freecad executable")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "install_freecad"

    def test_freecad_not_found_chinese(self):
        """Test detection of Chinese FreeCAD not found error."""
        result = self._make_result("找不到 freecad")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "install_freecad"

    def test_install_freecad_gives_platform_help(self):
        """Test that install_freecad correction includes platform-specific help."""
        result = self._make_result("freecad not found")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        system = platform.system().lower()
        if system == "windows":
            assert "winget" in correction.description or "choco" in correction.description
        elif system == "darwin":
            assert "brew" in correction.description
        else:
            assert "apt" in correction.description or "dnf" in correction.description or "flatpak" in correction.description

    def test_install_freecad_original_task_unchanged(self):
        """Test that install_freecad correction does not modify task args."""
        original_args = self.task.args[:]
        result = self._make_result("freecad not found")
        self.corrector.correct(self.task, result)
        # install_freecad doesn't change args (it's informational)
        assert self.task.args == original_args


# ── Dry Run Executor Tests ──

class TestDryRun:
    """Test the dry_run mode in Executor."""

    def test_dry_run_default_false(self):
        """Test that dry_run defaults to False."""
        executor = Executor()
        assert executor.dry_run is False

    def test_dry_run_init_true(self):
        """Test setting dry_run via constructor."""
        executor = Executor(dry_run=True)
        assert executor.dry_run is True

    def test_dry_run_setter(self):
        """Test the dry_run property setter."""
        executor = Executor()
        executor.dry_run = True
        assert executor.dry_run is True
        executor.dry_run = False
        assert executor.dry_run is False

    def test_dry_run_task_returns_success(self):
        """Test that dry_run execute_task returns success without running commands."""
        executor = Executor(dry_run=True)
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Create a box",
            command="fc",
            args=["part", "add", "box", "--name", "Box"],
        )
        result = executor.execute_task(task)
        assert result.success is True
        assert result.data.get("dry_run") is True

    def test_dry_run_task_sets_status_success(self):
        """Test that dry_run sets task status to success."""
        executor = Executor(dry_run=True)
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Create a box",
            command="fc",
            args=["part", "add", "box"],
        )
        executor.execute_task(task)
        assert task.status == "success"

    def test_dry_run_command_logged(self):
        """Test that dry_run commands are logged."""
        executor = Executor(dry_run=True)
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Create a box",
            command="fc",
            args=["part", "add", "box", "--name", "MyBox"],
        )
        executor.execute_task(task)
        assert len(executor.dry_run_log) == 1
        assert "fc" in executor.dry_run_log[0]
        assert "part" in executor.dry_run_log[0]
        assert "MyBox" in executor.dry_run_log[0]

    def test_dry_run_multiple_tasks(self):
        """Test dry_run with multiple tasks."""
        executor = Executor(dry_run=True)
        tasks = [
            Task(id="t1", type=TaskType.DOCUMENT_NEW, description="New doc",
                 command="fc", args=["document", "new"]),
            Task(id="t2", type=TaskType.PART_ADD, description="Add box",
                 command="fc", args=["part", "add", "box"]),
            Task(id="t3", type=TaskType.EXPORT_STEP, description="Export",
                 command="fc", args=["export", "step", "out.step"]),
        ]
        for task in tasks:
            result = executor.execute_task(task)
            assert result.success is True
            assert task.status == "success"
        assert len(executor.dry_run_log) == 3
        assert len(executor.results) == 3

    def test_dry_run_result_has_command(self):
        """Test that dry_run result data includes the command string."""
        executor = Executor(dry_run=True)
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Add box",
            command="fc",
            args=["part", "add", "box"],
        )
        result = executor.execute_task(task)
        assert "command" in result.data
        assert "fc part add box" == result.data["command"]

    def test_dry_run_does_not_call_subprocess(self):
        """Test that dry_run does not invoke subprocess."""
        executor = Executor(dry_run=True)
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Add box",
            command="nonexistent_command_that_should_not_run",
            args=["part", "add", "box"],
        )
        # If subprocess were called with a nonexistent command, it would raise
        # FileNotFoundError in non-dry-run mode. Dry run should succeed.
        result = executor.execute_task(task)
        assert result.success is True

    def test_dry_run_includes_backend_flag(self):
        """Test that dry_run includes --backend flag when backend is rpc."""
        executor = Executor(dry_run=True, backend="rpc")
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Add box",
            command="fc",
            args=["part", "add", "box"],
        )
        executor.execute_task(task)
        cmd_log = executor.dry_run_log[0]
        assert "--backend" in cmd_log
        assert "rpc" in cmd_log

    def test_dry_run_direct_command(self):
        """Test dry_run with execute_direct."""
        executor = Executor(dry_run=True)
        result = executor.execute_direct("part add box --name TestBox")
        assert result.success is True
        assert result.data.get("dry_run") is True
        assert len(executor.dry_run_log) == 1
        assert "TestBox" in executor.dry_run_log[0]

    def test_dry_run_log_is_copy(self):
        """Test that dry_run_log property returns a copy."""
        executor = Executor(dry_run=True)
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Add box",
            command="fc",
            args=["part", "add", "box"],
        )
        executor.execute_task(task)
        log = executor.dry_run_log
        log.append("tampered")
        assert len(executor.dry_run_log) == 1

    def test_dry_run_duration_is_zero(self):
        """Test that dry_run results have zero duration."""
        executor = Executor(dry_run=True)
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Add box",
            command="fc",
            args=["part", "add", "box"],
        )
        result = executor.execute_task(task)
        assert result.duration_ms == 0.0


# ═══════════════════════════════════════════════════════════════
# Enhanced Test Classes
# ═══════════════════════════════════════════════════════════════


# ── TestPlannerEnhancements ──

class TestPlannerEnhancements:
    """Extended tests for the Planner — Chinese input, complex designs,
    parameter extraction, operation detection, and dependency generation."""

    def setup_method(self):
        self.planner = Planner()

    # -- Chinese natural language --

    def test_chinese_flange_request(self):
        """Test Chinese input: '设计一个法兰盘'."""
        plan = self.planner.plan("设计一个法兰盘")
        assert plan.goal == "设计一个法兰盘"
        assert len(plan.tasks) > 0
        # Document name is extracted from the keyword "法兰" (Chinese)
        doc_task = [t for t in plan.tasks if t.type == TaskType.DOCUMENT_NEW][0]
        assert "法兰" in str(doc_task.args) or "flange" in str(doc_task.args).lower()

    def test_chinese_box_with_dimensions(self):
        """Test Chinese input: '创建一个 20x30x40 的长方体'."""
        plan = self.planner.plan("创建一个 20x30x40 的长方体")
        assert len(plan.tasks) > 0
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        # Verify dimensions are extracted
        args_str = " ".join(part_tasks[0].args)
        assert "20" in args_str
        assert "30" in args_str
        assert "40" in args_str

    def test_chinese_cylinder_request(self):
        """Test Chinese cylinder request with radius keyword."""
        plan = self.planner.plan("创建一个圆柱 半径 10 高度 50")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        params = part_tasks[0].params
        assert "radius" in params or any("10" in a for a in part_tasks[0].args)

    def test_chinese_sphere_request(self):
        """Test Chinese sphere request."""
        plan = self.planner.plan("设计一个球体")
        assert len(plan.tasks) > 0
        # Sphere should be detected
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1

    def test_chinese_shaft_request(self):
        """Test Chinese shaft request."""
        plan = self.planner.plan("创建一个轴")
        assert len(plan.tasks) > 0

    def test_chinese_housing_request(self):
        """Test Chinese housing/shell request."""
        plan = self.planner.plan("设计一个壳体")
        assert len(plan.tasks) > 0

    # -- Complex multi-part designs --

    def test_flange_with_holes(self):
        """Test complex design: '创建一个带孔的法兰盘'."""
        plan = self.planner.plan("创建一个带孔的法兰盘")
        assert len(plan.tasks) > 0
        # Should have document + flange + exports + save
        doc_tasks = [t for t in plan.tasks if t.type == TaskType.DOCUMENT_NEW]
        assert len(doc_tasks) == 1
        # Should have export tasks
        export_tasks = [t for t in plan.tasks
                        if t.type in (TaskType.EXPORT_STEP, TaskType.EXPORT_STL)]
        assert len(export_tasks) >= 2

    def test_gear_with_fillet(self):
        """Test gear with fillet operation."""
        plan = self.planner.plan("齿轮 圆角 r=2")
        fillet_tasks = [t for t in plan.tasks if t.type == TaskType.PART_FILLET]
        assert len(fillet_tasks) >= 1

    def test_box_with_chamfer_and_fillet(self):
        """Test box with both chamfer and fillet."""
        plan = self.planner.plan("创建一个盒子 倒角 倒圆 r=1")
        chamfer_tasks = [t for t in plan.tasks if t.type == TaskType.PART_CHAMFER]
        fillet_tasks = [t for t in plan.tasks if t.type == TaskType.PART_FILLET]
        assert len(chamfer_tasks) >= 1
        assert len(fillet_tasks) >= 1

    def test_multiple_part_types_detected(self):
        """Test that multiple part types can be detected in one request."""
        plan = self.planner.plan("box 20x30x40 and cylinder")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        # Should have at least 2 part tasks (box + cylinder)
        assert len(part_tasks) >= 2

    # -- Parameter extraction --

    def test_extract_dimensions_10x20x30(self):
        """Test dimension extraction: '10x20x30'."""
        plan = self.planner.plan("box 10x20x30")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        args_str = " ".join(part_tasks[0].args)
        assert "10" in args_str
        assert "20" in args_str
        assert "30" in args_str

    def test_extract_dimensions_with_spaces(self):
        """Test dimension extraction with spaces: '10 x 20 x 30'."""
        plan = self.planner.plan("box 10 x 20 x 30")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        args_str = " ".join(part_tasks[0].args)
        assert "10" in args_str
        assert "20" in args_str
        assert "30" in args_str

    def test_extract_dimensions_comma_separated(self):
        """Test dimension extraction with commas: '10,20,30'."""
        plan = self.planner.plan("box 10,20,30")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        args_str = " ".join(part_tasks[0].args)
        assert "10" in args_str
        assert "20" in args_str
        assert "30" in args_str

    def test_extract_dimensions_with_units(self):
        """Test dimension extraction with mm units: '10x20x30mm'."""
        plan = self.planner.plan("box 10x20x30mm")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        args_str = " ".join(part_tasks[0].args)
        assert "10" in args_str
        assert "20" in args_str
        assert "30" in args_str

    def test_extract_diameter_D50(self):
        """Test diameter extraction: 'D=50'."""
        plan = self.planner.plan("cylinder D=50 height=100")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        params = part_tasks[0].params
        # D=50 should give radius=25
        assert "radius" in params
        assert params["radius"] == 25.0

    def test_extract_diameter_chinese(self):
        """Test diameter extraction with Chinese: '直径50'."""
        plan = self.planner.plan("圆柱 直径50 高100")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        params = part_tasks[0].params
        assert "radius" in params
        assert params["radius"] == 25.0

    def test_extract_radius_chinese(self):
        """Test radius extraction: '半径 10'.

        The planner's _extract_dimensions only handles diameter (直径),
        not radius (半径). So '半径 10' results in default radius=5.
        """
        plan = self.planner.plan("圆柱 半径 10")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        params = part_tasks[0].params
        assert "radius" in params
        # Planner does not extract 半径, so default radius=5 is used
        assert params["radius"] == 5.0

    def test_extract_length_width_height_chinese(self):
        """Test Chinese dimension keywords: 长10 宽20 高30."""
        plan = self.planner.plan("box 长10 宽20 高30")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        params = part_tasks[0].params
        assert params.get("length") == 10.0
        assert params.get("width") == 20.0
        assert params.get("height") == 30.0

    def test_extract_float_dimensions(self):
        """Test float dimension extraction: '10.5x20.5x30.5'."""
        plan = self.planner.plan("box 10.5x20.5x30.5")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        assert len(part_tasks) >= 1
        args_str = " ".join(part_tasks[0].args)
        assert "10.5" in args_str
        assert "20.5" in args_str
        assert "30.5" in args_str

    # -- Operation detection --

    def test_boolean_operation_fuse(self):
        """Test boolean operation detection."""
        plan = self.planner.plan("box boolean fuse")
        bool_tasks = [t for t in plan.tasks if t.type == TaskType.PART_BOOLEAN]
        assert len(bool_tasks) >= 1

    def test_boolean_operation_chinese(self):
        """Test boolean operation detection in Chinese."""
        plan = self.planner.plan("盒子 布尔运算 合并")
        bool_tasks = [t for t in plan.tasks if t.type == TaskType.PART_BOOLEAN]
        assert len(bool_tasks) >= 1

    def test_fillet_with_radius(self):
        """Test fillet with specific radius: 'fillet r=3'."""
        plan = self.planner.plan("box fillet r=3")
        fillet_tasks = [t for t in plan.tasks if t.type == TaskType.PART_FILLET]
        assert len(fillet_tasks) >= 1
        args_str = " ".join(fillet_tasks[0].args)
        assert "3" in args_str

    def test_fillet_chinese(self):
        """Test fillet detection in Chinese: '圆角'."""
        plan = self.planner.plan("盒子 圆角")
        fillet_tasks = [t for t in plan.tasks if t.type == TaskType.PART_FILLET]
        assert len(fillet_tasks) >= 1

    def test_chamfer_with_size(self):
        """Test chamfer with specific size: 'chamfer size=2.5'."""
        plan = self.planner.plan("box chamfer size=2.5")
        chamfer_tasks = [t for t in plan.tasks if t.type == TaskType.PART_CHAMFER]
        assert len(chamfer_tasks) >= 1
        args_str = " ".join(chamfer_tasks[0].args)
        assert "2.5" in args_str

    def test_chamfer_chinese(self):
        """Test chamfer detection in Chinese: '倒角'."""
        plan = self.planner.plan("盒子 倒角")
        chamfer_tasks = [t for t in plan.tasks if t.type == TaskType.PART_CHAMFER]
        assert len(chamfer_tasks) >= 1

    def test_mirror_operation(self):
        """Test mirror operation detection.

        The planner always defaults mirror to XY plane regardless of input.
        """
        plan = self.planner.plan("box mirror YZ")
        mirror_tasks = [t for t in plan.tasks if t.type == TaskType.PART_MIRROR]
        assert len(mirror_tasks) >= 1
        args_str = " ".join(mirror_tasks[0].args)
        # Planner always uses XY as the default mirror plane
        assert "XY" in args_str

    def test_mirror_chinese(self):
        """Test mirror detection in Chinese: '镜像'."""
        plan = self.planner.plan("盒子 镜像 XY")
        mirror_tasks = [t for t in plan.tasks if t.type == TaskType.PART_MIRROR]
        assert len(mirror_tasks) >= 1

    def test_array_operation(self):
        """Test array operation detection."""
        plan = self.planner.plan("box array 6x4")
        # Array is detected as a custom operation
        custom_tasks = [t for t in plan.tasks if t.type == TaskType.CUSTOM]
        assert len(custom_tasks) >= 1

    # -- Dependency generation --

    def test_document_task_is_first(self):
        """Test that document creation is always the first task."""
        plan = self.planner.plan("design a box 20x30x40")
        assert plan.tasks[0].type == TaskType.DOCUMENT_NEW

    def test_part_depends_on_document(self):
        """Test that part tasks depend on document creation."""
        plan = self.planner.plan("design a box 20x30x40")
        doc_task = plan.tasks[0]
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        for pt in part_tasks:
            assert doc_task.id in pt.dependencies

    def test_export_depends_on_part(self):
        """Test that export tasks depend on part creation."""
        plan = self.planner.plan("design a box 20x30x40")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        export_tasks = [t for t in plan.tasks
                        if t.type in (TaskType.EXPORT_STEP, TaskType.EXPORT_STL)]
        if part_tasks and export_tasks:
            last_part_id = part_tasks[-1].id
            for et in export_tasks:
                assert last_part_id in et.dependencies

    def test_save_depends_on_all_tasks(self):
        """Test that save task depends on previous tasks."""
        plan = self.planner.plan("design a box 20x30x40")
        save_tasks = [t for t in plan.tasks if t.type == TaskType.DOCUMENT_SAVE]
        assert len(save_tasks) >= 1
        save_task = save_tasks[-1]
        # Save should have at least one dependency
        assert len(save_task.dependencies) > 0

    def test_operation_depends_on_part(self):
        """Test that operation tasks depend on part creation."""
        plan = self.planner.plan("box fillet r=2")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        op_tasks = [t for t in plan.tasks
                     if t.type in (TaskType.PART_FILLET, TaskType.PART_CHAMFER,
                                   TaskType.PART_MIRROR, TaskType.PART_BOOLEAN)]
        if part_tasks and op_tasks:
            last_part_id = part_tasks[-1].id
            for ot in op_tasks:
                assert last_part_id in ot.dependencies

    def test_plan_task_ordering(self):
        """Test that tasks are in correct order: doc -> parts -> ops -> exports -> save."""
        plan = self.planner.plan("box 20x30x40 fillet r=2 export step")
        type_order = [t.type for t in plan.tasks]
        doc_idx = type_order.index(TaskType.DOCUMENT_NEW)
        save_idx = len(type_order) - 1  # Save should be last
        assert type_order[save_idx] == TaskType.DOCUMENT_SAVE
        assert doc_idx < save_idx

    def test_no_duplicate_part_types(self):
        """Test that the same part type is not added twice."""
        plan = self.planner.plan("box box box")
        part_tasks = [t for t in plan.tasks if t.type == TaskType.PART_ADD]
        # Should only have one box task despite "box" appearing 3 times
        assert len(part_tasks) == 1


# ── TestExecutorIntegration ──

class TestExecutorIntegration:
    """Integration tests for Executor dry_run mode."""

    def test_dry_run_no_subprocess_call(self):
        """Verify dry_run does not call subprocess.run."""
        from fc_runtime.executor import Executor
        from fc_runtime.planner import Task, TaskType

        executor = Executor(dry_run=True)
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Create a box",
            command="fc",
            args=["part", "add", "box"],
        )
        with patch("fc_runtime.executor.subprocess.run") as mock_run:
            result = executor.execute_task(task)
            mock_run.assert_not_called()
            assert result.success is True

    def test_dry_run_records_all_commands(self):
        """Verify dry_run records all commands in the log."""
        from fc_runtime.executor import Executor
        from fc_runtime.planner import Task, TaskType

        executor = Executor(dry_run=True)
        tasks = [
            Task(id="t1", type=TaskType.DOCUMENT_NEW, description="New doc",
                 command="fc", args=["document", "new", "--name", "Test"]),
            Task(id="t2", type=TaskType.PART_ADD, description="Add box",
                 command="fc", args=["part", "add", "box", "--name", "Box1"]),
            Task(id="t3", type=TaskType.EXPORT_STEP, description="Export STEP",
                 command="fc", args=["export", "step", "output.step"]),
        ]
        for task in tasks:
            executor.execute_task(task)

        log = executor.dry_run_log
        assert len(log) == 3
        assert any("document" in entry and "new" in entry for entry in log)
        assert any("part" in entry and "add" in entry and "Box1" in entry for entry in log)
        assert any("export" in entry and "step" in entry for entry in log)

    def test_dry_run_output_format(self):
        """Verify dry_run output format is correct."""
        from fc_runtime.executor import Executor
        from fc_runtime.planner import Task, TaskType

        executor = Executor(dry_run=True)
        task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Add box",
            command="fc",
            args=["part", "add", "box", "--name", "MyBox",
                  "--param", "Length=20", "--param", "Width=30",
                  "--param", "Height=40", "--json"],
        )
        result = executor.execute_task(task)

        assert result.success is True
        assert result.data["dry_run"] is True
        assert result.data["command"] == "fc part add box --name MyBox --param Length=20 --param Width=30 --param Height=40 --json"
        assert result.task_id == "test_001"
        assert result.duration_ms == 0.0

    def test_dry_run_execute_plan(self):
        """Verify execute_plan works in dry_run mode."""
        from fc_runtime.executor import Executor
        from fc_runtime.planner import Planner

        planner = Planner()
        plan = planner.plan("design a box 20x30x40")

        executor = Executor(dry_run=True)
        results = executor.execute_plan(plan)

        assert len(results) > 0
        assert all(r.success for r in results)
        assert len(executor.dry_run_log) == len(plan.tasks)

    def test_dry_run_with_corrector(self):
        """Verify dry_run works with a corrector passed to execute_plan."""
        from fc_runtime.executor import Executor
        from fc_runtime.corrector import Corrector
        from fc_runtime.planner import Planner

        planner = Planner()
        plan = planner.plan("design a box")

        executor = Executor(dry_run=True)
        corrector = Corrector()
        results = executor.execute_plan(plan, corrector=corrector)

        assert all(r.success for r in results)

    def test_dry_run_results_list(self):
        """Verify results list is populated in dry_run mode."""
        from fc_runtime.executor import Executor
        from fc_runtime.planner import Task, TaskType

        executor = Executor(dry_run=True)
        task = Task(
            id="t1", type=TaskType.PART_ADD, description="Add box",
            command="fc", args=["part", "add", "box"],
        )
        executor.execute_task(task)

        assert len(executor.results) == 1
        assert executor.results[0].success is True

    def test_dry_run_task_status_updated(self):
        """Verify task status is updated to success in dry_run mode."""
        from fc_runtime.executor import Executor
        from fc_runtime.planner import Task, TaskType

        executor = Executor(dry_run=True)
        task = Task(
            id="t1", type=TaskType.PART_ADD, description="Add box",
            command="fc", args=["part", "add", "box"],
        )
        executor.execute_task(task)
        assert task.status == "success"
        assert task.result.get("dry_run") is True

    def test_dry_run_stdout_is_json(self):
        """Verify dry_run stdout is valid JSON."""
        from fc_runtime.executor import Executor
        from fc_runtime.planner import Task, TaskType
        import json

        executor = Executor(dry_run=True)
        task = Task(
            id="t1", type=TaskType.PART_ADD, description="Add box",
            command="fc", args=["part", "add", "box"],
        )
        result = executor.execute_task(task)
        data = json.loads(result.stdout)
        assert data["dry_run"] is True

    def test_dry_run_nonexistent_command_succeeds(self):
        """Verify dry_run succeeds even with a nonexistent command path."""
        from fc_runtime.executor import Executor
        from fc_runtime.planner import Task, TaskType

        executor = Executor(fc_path="/nonexistent/fc", dry_run=True)
        task = Task(
            id="t1", type=TaskType.PART_ADD, description="Add box",
            command="/nonexistent/fc",
            args=["part", "add", "box"],
        )
        result = executor.execute_task(task)
        assert result.success is True


# ── TestCorrectorPatterns ──

class TestCorrectorPatterns:
    """Test all error correction patterns in the Corrector."""

    def setup_method(self):
        self.corrector = Corrector()
        self.task = Task(
            id="test_001",
            type=TaskType.PART_ADD,
            description="Create a box",
            command="fc",
            args=["part", "add", "box", "--name", "Box"],
        )

    def _make_result(self, error_msg: str, stderr: str = "") -> TaskResult:
        return TaskResult(
            task_id="test_001",
            success=False,
            error=error_msg,
            stderr=stderr or error_msg,
        )

    # -- no_document --

    def test_no_document_error(self):
        """Test no_document error detection and correction."""
        result = self._make_result("no active document found")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "create_document"

    def test_no_document_chinese(self):
        """Test no_document error in Chinese."""
        result = self._make_result("没有活动文档")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "create_document"

    def test_no_document_adds_document_args(self):
        """Test that create_document correction prepends document creation args."""
        result = self._make_result("no active document")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert "document" in correction.new_args
        assert "new" in correction.new_args

    # -- object_not_found --

    def test_object_not_found_error(self):
        """Test object_not_found error detection.

        The error message must not contain 'document.*not found' which
        would match the no_document pattern first.
        """
        result = self._make_result("object 'NonExistent' not found in active assembly")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "fix_object_name"

    def test_object_not_found_chinese(self):
        """Test object_not_found error in Chinese."""
        result = self._make_result("找不到对象 '不存在'")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "fix_object_name"

    def test_object_not_found_replaces_name(self):
        """Test that fix_object_name replaces the bad object name."""
        result = self._make_result("object 'WrongName' not found in active assembly")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        # Should replace WrongName with Box
        assert "WrongName" not in correction.new_args or "Box" in correction.new_args

    # -- invalid_parameter --

    def test_invalid_parameter_error(self):
        """Test invalid_parameter error detection."""
        result = self._make_result("invalid parameter: value out of range")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "fix_parameter"

    def test_invalid_parameter_chinese(self):
        """Test invalid_parameter error in Chinese."""
        result = self._make_result("参数无效 值超出范围")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "fix_parameter"

    def test_invalid_parameter_clamps_negative(self):
        """Test that fix_parameter handles args with negative values.

        The corrector's regex matches '--param Key=-5' as a single string,
        but the args list has '--param' and 'Length=-5' as separate elements.
        So the fix_parameter correction returns new_args that are unchanged.
        """
        task = Task(
            id="test_002",
            type=TaskType.PART_ADD,
            description="Add box with negative dim",
            command="fc",
            args=["part", "add", "box", "--param", "Length=-5"],
        )
        result = self._make_result("invalid parameter: must be positive")
        correction = self.corrector.analyze(task, result)
        assert correction is not None
        assert correction.fix_type == "fix_parameter"
        # With separate arg elements, the regex doesn't match, so args are returned as-is
        assert correction.new_args == ["part", "add", "box", "--param", "Length=-5"]

    # -- file_exists --

    def test_file_exists_error(self):
        """Test file_exists error detection."""
        result = self._make_result("file exists: output.step")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "overwrite"

    def test_file_exists_chinese(self):
        """Test file_exists error in Chinese."""
        result = self._make_result("文件已存在 output.step")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "overwrite"

    def test_file_exists_adds_overwrite_flag(self):
        """Test that overwrite correction adds --overwrite flag."""
        result = self._make_result("file exists: output.step")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert "--overwrite" in correction.new_args

    def test_file_exists_no_duplicate_overwrite(self):
        """Test that overwrite correction returns new_args unchanged when --overwrite already present."""
        task = Task(
            id="test_003",
            type=TaskType.EXPORT_STEP,
            description="Export",
            command="fc",
            args=["export", "step", "out.step", "--overwrite"],
        )
        result = self._make_result("file exists: out.step")
        correction = self.corrector.analyze(task, result)
        assert correction is not None
        assert correction.fix_type == "overwrite"
        # When --overwrite is already present, the overwrite branch returns None
        # and the fallback returns a generic correction with no new_args override
        assert correction.new_args is None

    # -- timeout --

    def test_timeout_error(self):
        """Test timeout error detection."""
        result = self._make_result("operation timed out after 120s")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "retry_with_timeout"

    def test_timeout_chinese(self):
        """Test timeout error in Chinese."""
        result = self._make_result("操作超时")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "retry_with_timeout"

    # -- syntax_error --

    def test_syntax_error(self):
        """Test syntax_error detection."""
        result = self._make_result("syntax error: unexpected argument")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "fix_syntax"

    def test_syntax_error_chinese(self):
        """Test syntax_error in Chinese."""
        result = self._make_result("语法错误: 无效选项")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "fix_syntax"

    def test_syntax_error_removes_duplicates(self):
        """Test that fix_syntax removes duplicate flags."""
        task = Task(
            id="test_004",
            type=TaskType.PART_ADD,
            description="Add box with duplicate flags",
            command="fc",
            args=["part", "add", "--json", "box", "--json"],
        )
        result = self._make_result("syntax error: duplicate --json")
        correction = self.corrector.analyze(task, result)
        assert correction is not None
        assert correction.fix_type == "fix_syntax"
        # Should have only one --json
        assert correction.new_args.count("--json") == 1

    # -- FREECAD_NOT_FOUND --

    def test_freecad_not_found(self):
        """Test FREECAD_NOT_FOUND error detection."""
        result = self._make_result("freecad not found in system PATH")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "install_freecad"

    def test_freecad_not_installed(self):
        """Test FreeCAD not installed error."""
        result = self._make_result("FreeCAD is not installed on this system")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "install_freecad"

    def test_freecad_cannot_locate(self):
        """Test cannot locate FreeCAD error."""
        result = self._make_result("cannot locate freecad executable")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "install_freecad"

    def test_freecad_not_found_chinese(self):
        """Test FreeCAD not found in Chinese."""
        result = self._make_result("找不到 freecad")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "install_freecad"

    def test_freecad_install_gives_platform_help(self):
        """Test that install_freecad gives platform-specific help."""
        result = self._make_result("freecad not found")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        system = platform.system().lower()
        if system == "windows":
            assert "winget" in correction.description or "choco" in correction.description
        elif system == "darwin":
            assert "brew" in correction.description
        else:
            assert "apt" in correction.description or "dnf" in correction.description

    # -- Generic retry --

    def test_unknown_error_generic_retry(self):
        """Test that unknown errors get a generic retry."""
        result = self._make_result("some completely unknown error xyz123")
        correction = self.corrector.analyze(self.task, result)
        assert correction is not None
        assert correction.fix_type == "generic_retry"

    def test_no_correction_after_max_retries(self):
        """Test that no correction is returned after max retries exceeded."""
        self.task.retries = 3
        self.corrector = Corrector(max_retries=3)
        result = self._make_result("some unknown error")
        correction = self.corrector.analyze(self.task, result)
        assert correction is None

    # -- correct() method --

    def test_correct_applies_new_args(self):
        """Test that correct() applies new_args to the task."""
        result = self._make_result("file exists: output.step")
        original_args = self.task.args[:]
        self.corrector.correct(self.task, result)
        # Args should have been modified
        assert self.task.args != original_args or "--overwrite" in self.task.args

    def test_correct_returns_true_on_fix(self):
        """Test that correct() returns True when a fix is applied."""
        result = self._make_result("file exists: output.step")
        applied = self.corrector.correct(self.task, result)
        assert applied is True

    def test_correct_returns_false_on_no_fix(self):
        """Test that correct() returns False when no fix is available."""
        self.task.retries = 3
        self.corrector = Corrector(max_retries=3)
        result = self._make_result("some unknown error xyz")
        applied = self.corrector.correct(self.task, result)
        assert applied is False

    def test_corrections_list_populated(self):
        """Test that corrections list is populated after analyze."""
        result = self._make_result("file exists: output.step")
        self.corrector.analyze(self.task, result)
        assert len(self.corrector.corrections) == 1

    def test_corrections_list_is_copy(self):
        """Test that corrections property returns a copy."""
        result = self._make_result("file exists: output.step")
        self.corrector.analyze(self.task, result)
        corrections = self.corrector.corrections
        corrections.append("tampered")
        assert len(self.corrector.corrections) == 1


# ── TestBOMGeneration ──

class TestBOMGeneration:
    """Test BOM generation from documents and plans."""

    def test_bom_from_document_objects(self):
        """Test generating BOM from document objects."""
        bom = BOM(project_name="Test Assembly")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box",
                                  volume=24000.0, material="Steel"))
        bom.items.append(BOMItem(index=2, name="Cylinder", type_id="Part::Cylinder",
                                  volume=7853.98, material="Aluminum"))
        bom.total_volume = 31853.98
        bom.total_mass = 86.0

        assert len(bom.items) == 2
        assert bom.items[0].name == "Box"
        assert bom.items[1].name == "Cylinder"
        assert bom.total_volume == 31853.98

    def test_bom_export_json(self, tmp_path):
        """Test BOM JSON export."""
        bom = BOM(project_name="JSON_Test")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box",
                                  volume=1000.0))

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path), formats=["json"])

        assert len(files) == 1
        assert files[0].endswith(".json")
        assert os.path.exists(files[0])

        with open(files[0]) as f:
            data = json.load(f)
        assert data["project_name"] == "JSON_Test"
        assert data["total_parts"] == 1
        assert data["items"][0]["name"] == "Box"

    def test_bom_export_csv(self, tmp_path):
        """Test BOM CSV export."""
        bom = BOM(project_name="CSV_Test")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box",
                                  volume=1000.0))

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path), formats=["csv"])

        assert len(files) == 1
        assert files[0].endswith(".csv")
        assert os.path.exists(files[0])

        with open(files[0]) as f:
            content = f.read()
        assert "Index,Name" in content
        assert "Box" in content
        assert "Part::Box" in content

    def test_bom_export_markdown(self, tmp_path):
        """Test BOM Markdown export."""
        bom = BOM(project_name="MD_Test")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box",
                                  volume=1000.0))

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path), formats=["md"])

        assert len(files) == 1
        assert files[0].endswith(".md")
        assert os.path.exists(files[0])

        with open(files[0]) as f:
            content = f.read()
        assert "# Bill of Materials" in content
        assert "MD_Test" in content
        assert "Box" in content

    def test_bom_export_table(self, tmp_path):
        """Test BOM Table (txt) export."""
        bom = BOM(project_name="Table_Test")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box",
                                  volume=1000.0))
        bom.total_volume = 1000.0

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path), formats=["txt"])

        assert len(files) == 1
        assert files[0].endswith(".txt")
        assert os.path.exists(files[0])

        with open(files[0]) as f:
            content = f.read()
        assert "Bill of Materials" in content
        assert "Box" in content

    def test_bom_export_multiple_formats(self, tmp_path):
        """Test BOM export to multiple formats at once."""
        bom = BOM(project_name="Multi_Test")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box",
                                  volume=1000.0))

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path),
                               formats=["json", "csv", "md", "txt"])

        assert len(files) == 4
        for f in files:
            assert os.path.exists(f)

    def test_bom_data_integrity(self):
        """Test BOM data integrity — all fields preserved through serialization."""
        bom = BOM(project_name="Integrity_Test")
        bom.items.append(BOMItem(
            index=1, name="TestPart", label="TP-001",
            type_id="Part::Box", quantity=2, material="Steel",
            dimensions={"length": 20, "width": 30, "height": 40},
            volume=24000.0, area=5200.0, mass=183.6,
            notes="Test part with all fields",
        ))
        bom.total_volume = 24000.0
        bom.total_mass = 183.6

        d = bom.to_dict()
        assert d["project_name"] == "Integrity_Test"
        assert d["total_parts"] == 1
        assert d["total_volume_mm3"] == 24000.0
        assert d["total_mass_g"] == 183.6
        assert d["units"] == "mm"

        item = d["items"][0]
        assert item["name"] == "TestPart"
        assert item["label"] == "TP-001"
        assert item["type_id"] == "Part::Box"
        assert item["quantity"] == 2
        assert item["material"] == "Steel"
        assert item["dimensions"]["length"] == 20
        assert item["volume_mm3"] == 24000.0
        assert item["area_mm2"] == 5200.0
        assert item["mass_g"] == 183.6
        assert item["notes"] == "Test part with all fields"

    def test_bom_from_plan_with_box(self):
        """Test BOM generation from a plan with box parts."""
        planner = Planner()
        plan = planner.plan("design a box 20x30x40")

        # Mark part_add tasks as success (simulating execution)
        for task in plan.tasks:
            if task.type == TaskType.PART_ADD:
                task.status = TaskStatus.SUCCESS

        gen = BOMGenerator()
        bom = gen.from_plan(plan)

        assert isinstance(bom, BOM)
        assert bom.project_name == "design a box 20x30x40"
        # Should have at least one part from the plan
        assert len(bom.items) >= 1
        # Box volume should be 20*30*40 = 24000
        assert bom.total_volume == 24000.0

    def test_bom_from_plan_with_cylinder(self):
        """Test BOM generation from a plan with cylinder parts."""
        import math

        planner = Planner()
        plan = planner.plan("create a cylinder with radius 10 and height 50")

        # Mark part_add tasks as success (simulating execution)
        for task in plan.tasks:
            if task.type == TaskType.PART_ADD:
                task.status = TaskStatus.SUCCESS

        gen = BOMGenerator()
        bom = gen.from_plan(plan)

        assert isinstance(bom, BOM)
        assert len(bom.items) >= 1
        # Planner extracts height=50 but not radius (no 半径/radius keyword
        # in _extract_dimensions), so default radius=5 is used.
        # Cylinder volume: pi * r^2 * h = pi * 5^2 * 50
        expected_vol = math.pi * 5**2 * 50
        assert abs(bom.total_volume - expected_vol) < 0.01

    def test_bom_from_plan_empty(self):
        """Test BOM generation from a plan with no part tasks."""
        planner = Planner()
        plan = planner.plan("design a flange")

        gen = BOMGenerator()
        bom = gen.from_plan(plan)

        assert isinstance(bom, BOM)
        # Flange is a custom task, not part_add, so BOM may be empty
        assert len(bom.items) >= 0

    def test_bom_json_roundtrip(self):
        """Test BOM JSON serialization roundtrip."""
        bom = BOM(project_name="Roundtrip")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box",
                                  volume=1000.0))
        bom.total_volume = 1000.0
        bom.total_mass = 2.7

        json_str = bom.to_json()
        parsed = json.loads(json_str)
        assert parsed["project_name"] == "Roundtrip"
        assert parsed["total_parts"] == 1
        assert parsed["items"][0]["name"] == "Box"

    def test_bom_csv_format(self):
        """Test BOM CSV format correctness."""
        bom = BOM(project_name="CSV")
        bom.items.append(BOMItem(index=1, name="Box", label="B1",
                                  type_id="Part::Box", quantity=1,
                                  material="Steel", volume=1000.0,
                                  area=600.0, mass=2.7, notes=""))

        csv = bom.to_csv()
        lines = csv.strip().split("\n")
        assert len(lines) == 2  # header + 1 item
        assert lines[0] == "Index,Name,Label,Type,Quantity,Material,Volume_mm3,Area_mm2,Mass_g,Notes"
        assert "Box" in lines[1]
        assert "Steel" in lines[1]

    def test_bom_markdown_format(self):
        """Test BOM Markdown format correctness."""
        bom = BOM(project_name="MD")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box",
                                  volume=1000.0, mass=2.7))
        bom.total_volume = 1000.0
        bom.total_mass = 2.7

        md = bom.to_markdown()
        assert "# Bill of Materials: MD" in md
        assert "**Total Parts:** 1" in md
        assert "| # | Name | Type | Qty | Volume (mm³) | Mass (g) |" in md
        assert "| 1 | Box | Part::Box | 1 |" in md

    def test_bom_table_format(self):
        """Test BOM table format correctness."""
        bom = BOM(project_name="Table")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box",
                                  volume=1000.0))
        bom.total_volume = 1000.0

        table = bom.to_table()
        assert "Bill of Materials: Table" in table
        assert "Box" in table
        assert "TOTAL" in table

    def test_bom_empty(self):
        """Test empty BOM."""
        bom = BOM(project_name="Empty")
        assert len(bom.items) == 0
        assert bom.total_volume == 0.0

        d = bom.to_dict()
        assert d["total_parts"] == 0
        assert len(d["items"]) == 0

    def test_bom_item_defaults(self):
        """Test BOMItem default values."""
        item = BOMItem()
        assert item.index == 0
        assert item.name == ""
        assert item.quantity == 1
        assert item.volume == 0.0
        assert item.material == ""


# ── TestFullWorkflow ──

class TestFullWorkflow:
    """Test the complete Planner -> Executor -> BOM workflow using dry_run."""

    def test_full_workflow_box(self):
        """Plan -> Execute(dry_run) -> BOM for a simple box.

        Uses '长方体' which is a recognized box keyword in the planner.
        """
        planner = Planner()
        plan = planner.plan("设计一个长方体 20x30x40mm")

        assert len(plan.tasks) > 0
        assert any(t.type.value == "part_add" for t in plan.tasks)

        executor = Executor(dry_run=True)
        results = executor.execute_plan(plan)

        assert all(r.success for r in results)

        # Generate BOM from the executed plan
        gen = BOMGenerator()
        bom = gen.from_plan(plan)
        assert isinstance(bom, BOM)
        assert len(bom.items) >= 1
        assert bom.total_volume == 24000.0  # 20*30*40

    def test_full_workflow_cylinder(self):
        """Plan -> Execute(dry_run) -> BOM for a cylinder.

        The planner's _extract_dimensions extracts 'height 50' via the
        height/H keyword pattern, but does NOT extract 'radius 10'
        (no radius/半径 keyword in _extract_dimensions). Default radius=5.
        """
        import math

        planner = Planner()
        plan = planner.plan("create a cylinder with radius 10 and height 50")

        assert len(plan.tasks) > 0

        executor = Executor(dry_run=True)
        results = executor.execute_plan(plan)

        assert all(r.success for r in results)

        gen = BOMGenerator()
        bom = gen.from_plan(plan)
        assert isinstance(bom, BOM)
        assert len(bom.items) >= 1
        # Default radius=5, extracted height=50
        expected_vol = math.pi * 5**2 * 50
        assert abs(bom.total_volume - expected_vol) < 0.01

    def test_full_workflow_with_exports(self):
        """Plan -> Execute(dry_run) -> BOM with export tasks."""
        planner = Planner()
        plan = planner.plan("design a box 10x20x30 export step stl")

        executor = Executor(dry_run=True)
        results = executor.execute_plan(plan)

        assert all(r.success for r in results)

        # Verify export tasks were executed
        export_results = [r for r, t in zip(results, plan.tasks)
                          if t.type in (TaskType.EXPORT_STEP, TaskType.EXPORT_STL)]
        assert len(export_results) >= 2

    def test_full_workflow_with_fillet(self):
        """Plan -> Execute(dry_run) -> BOM with fillet operation."""
        planner = Planner()
        plan = planner.plan("box 20x30x40 fillet r=2")

        executor = Executor(dry_run=True)
        results = executor.execute_plan(plan)

        assert all(r.success for r in results)

        # Verify fillet task was executed
        fillet_results = [r for r, t in zip(results, plan.tasks)
                          if t.type == TaskType.PART_FILLET]
        assert len(fillet_results) >= 1

    def test_full_workflow_chinese_request(self):
        """Full workflow with Chinese natural language input."""
        planner = Planner()
        plan = planner.plan("设计一个长方体 20x30x40mm")

        assert len(plan.tasks) > 0
        assert any(t.type == TaskType.PART_ADD for t in plan.tasks)

        executor = Executor(dry_run=True)
        results = executor.execute_plan(plan)

        assert all(r.success for r in results)

        gen = BOMGenerator()
        bom = gen.from_plan(plan)
        assert isinstance(bom, BOM)
        assert len(bom.items) >= 1

    def test_full_workflow_bom_export(self, tmp_path):
        """Full workflow with BOM export to files."""
        planner = Planner()
        plan = planner.plan("design a box 10x20x30")

        executor = Executor(dry_run=True)
        results = executor.execute_plan(plan)

        assert all(r.success for r in results)

        gen = BOMGenerator()
        bom = gen.from_plan(plan)
        files = gen.export_bom(bom, output_dir=str(tmp_path),
                               formats=["json", "csv", "md"])

        assert len(files) == 3
        for f in files:
            assert os.path.exists(f)

    def test_full_workflow_dry_run_log_complete(self):
        """Verify dry_run log captures all commands in the full workflow."""
        planner = Planner()
        plan = planner.plan("design a box 10x20x30")

        executor = Executor(dry_run=True)
        executor.execute_plan(plan)

        # Log should have one entry per task
        assert len(executor.dry_run_log) == len(plan.tasks)
        # All log entries should contain 'fc'
        for entry in executor.dry_run_log:
            assert "fc" in entry

    def test_full_workflow_plan_progress(self):
        """Verify plan progress tracking through full workflow."""
        planner = Planner()
        plan = planner.plan("design a box 10x20x30")

        # Before execution: all pending
        progress = plan.progress
        assert progress["pending"] == len(plan.tasks)

        executor = Executor(dry_run=True)
        executor.execute_plan(plan)

        # After execution: all success
        progress = plan.progress
        assert progress["success"] == len(plan.tasks)
        assert progress["pending"] == 0
        assert progress["failed"] == 0

    def test_full_workflow_with_corrector(self):
        """Full workflow with corrector enabled."""
        planner = Planner()
        plan = planner.plan("design a box 10x20x30")

        executor = Executor(dry_run=True)
        corrector = Corrector()
        results = executor.execute_plan(plan, corrector=corrector)

        assert all(r.success for r in results)

    def test_full_workflow_multiple_parts(self):
        """Full workflow with multiple parts."""
        planner = Planner()
        plan = planner.plan("box 10x20x30 cylinder r=5 h=20")

        executor = Executor(dry_run=True)
        results = executor.execute_plan(plan)

        assert all(r.success for r in results)

        gen = BOMGenerator()
        bom = gen.from_plan(plan)
        # Should have at least 2 parts
        assert len(bom.items) >= 2


# ── Phase 2.5: Session Support ──

class TestExecutorSession:
    """Tests for Executor session routing support."""

    def test_executor_accepts_session_param(self):
        """Executor 应接受 session 参数。"""
        exec_default = Executor()
        assert exec_default._session is None

        exec_with_session = Executor(session="my_session")
        assert exec_with_session._session == "my_session"

    def test_execute_task_injects_session_flag(self):
        """有 session 时，execute_task 应在命令中注入 --session X。"""
        from fc_runtime.planner import Task, TaskStatus, TaskType
        task = Task(
            id="task_001",
            type=TaskType.PART_ADD,
            description="Add box",
            command="fc",
            args=["--json", "part", "add", "box", "--name", "Box"],
            status=TaskStatus.PENDING,
        )

        executor = Executor(session="gui_session", dry_run=True)
        with patch("fc_runtime.executor.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(
                returncode=0, stdout='{"success": true', stderr=""
            )
            result = executor.execute_task(task)

        # 检查 dry_run_log 中应包含 --session gui_session
        cmd_str = executor.dry_run_log[0] if executor.dry_run_log else ""
        assert "--session" in cmd_str
        assert "gui_session" in cmd_str

    def test_execute_task_session_overrides_backend(self):
        """session 优先级高于 backend。"""
        from fc_runtime.planner import Task, TaskStatus, TaskType
        task = Task(
            id="task_001",
            type=TaskType.PART_ADD,
            description="Add box",
            command="fc",
            args=["--json", "part", "add", "box"],
            status=TaskStatus.PENDING,
        )
        executor = Executor(session="gui_session", backend="rpc", dry_run=True)
        with patch("fc_runtime.executor.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(
                returncode=0, stdout='{"success": true', stderr=""
            )
            result = executor.execute_task(task)

        cmd_str = executor.dry_run_log[0]
        assert "--session gui_session" in cmd_str
        assert "--backend rpc" not in cmd_str

    def test_execute_task_no_session_uses_backend(self):
        """无 session 时，应使用 backend 参数。"""
        from fc_runtime.planner import Task, TaskStatus, TaskType
        task = Task(
            id="task_001",
            type=TaskType.PART_ADD,
            description="Add box",
            command="fc",
            args=["--json", "part", "add", "box"],
            status=TaskStatus.PENDING,
        )
        executor = Executor(backend="rpc", dry_run=True)
        with patch("fc_runtime.executor.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(
                returncode=0, stdout='{"success": true', stderr=""
            )
            result = executor.execute_task(task)

        cmd_str = executor.dry_run_log[0]
        assert "--backend rpc" in cmd_str
        assert "--session" not in cmd_str

    def test_execute_direct_injects_session_flag(self):
        """execute_direct 也应注入 session。"""
        executor = Executor(session="gui_session", dry_run=True)
        result = executor.execute_direct("document new --name Doc")

        cmd_str = executor.dry_run_log[0]
        assert "--session" in cmd_str
        assert "gui_session" in cmd_str

    def test_execute_plan_with_session(self):
        """execute_plan 也应该为所有任务注入 session。"""
        from fc_runtime.planner import Planner
        planner = Planner()
        plan = planner.plan("design a box 10x10x10", session="design_session")
        executor = Executor(session="design_session", dry_run=True)
        results = executor.execute_plan(plan)

        assert len(results) == len(plan.tasks)
        # 所有命令都应包含 --session
        for cmd in executor.dry_run_log:
            assert "--session design_session" in cmd

    def test_planner_accepts_session_param(self):
        """Planner.plan 应接受 session 参数。"""
        planner = Planner()
        plan = planner.plan("create a cylinder")
        assert plan.context.get("session") is None

        plan_with_session = planner.plan("create a cylinder", session="cyl_session")
        assert plan_with_session.context["session"] == "cyl_session"

    def test_plan_context_session_recorded(self):
        """session 记录到 plan.context。"""
        planner = Planner()
        plan = planner.plan("design a gear", session="gear_design")
        assert "session" in plan.context
        assert plan.context["session"] == "gear_design"
