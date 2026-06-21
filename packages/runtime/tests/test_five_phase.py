"""Tests for five-phase execution flow output."""

import pytest
from fc_runtime.planner import Planner, Plan, Task, TaskType, TaskStatus


class TestFivePhaseOutput:
    """Test the five-phase execution flow reporting."""

    def setup_method(self):
        self.planner = Planner()

    def test_phase1_tool_selection(self):
        """Phase 1: Tool selection lists all command groups and commands."""
        plan = self.planner.plan("design a box 20x30x40mm")
        output = plan.to_phase1_tool_selection()
        assert "Phase 1: Tool Selection" in output
        assert "document" in output
        assert "part" in output
        assert "export" in output
        assert "Command Groups" in output
        assert "Commands" in output

    def test_phase2_task_decomposition(self):
        """Phase 2: Task decomposition lists all steps."""
        plan = self.planner.plan("design a box 20x30x40mm")
        output = plan.to_phase2_task_decomposition()
        assert "Phase 2: Task Decomposition" in output
        assert "Step" in output
        assert "Operation" in output
        assert "Dependencies" in output
        # Should have at least: document_new, part_add, export_step, export_stl, document_save
        assert len(plan.tasks) >= 5

    def test_phase3_coord_dependencies(self):
        """Phase 3: Coordinate and dependency calculation."""
        plan = self.planner.plan("design a box 20x30x40mm")
        output = plan.to_phase3_coord_dependencies()
        assert "Phase 3: Coordinate & Dependency Calculation" in output
        assert "Coordinates" in output
        assert "Dependency Elements" in output
        assert "Topology" in output

    def test_phase3_box_coords_populated(self):
        """Phase 3: Box task should have coordinate metadata."""
        plan = self.planner.plan("design a box 20x30x40mm")
        box_task = None
        for t in plan.tasks:
            if t.type == TaskType.PART_ADD:
                box_task = t
                break
        assert box_task is not None
        assert "20" in box_task.phase3_coords
        assert "30" in box_task.phase3_coords
        assert "40" in box_task.phase3_coords

    def test_phase4_dependency_validation(self):
        """Phase 4: Dependency validation checks all dependencies."""
        plan = self.planner.plan("design a box 20x30x40mm")
        output = plan.to_phase4_dependency_validation()
        assert "Phase 4: Dependency Validation" in output
        assert "PASS" in output
        assert "ALL VALID" in output

    def test_phase5_commands(self):
        """Phase 5: Command output with comments."""
        plan = self.planner.plan("design a box 20x30x40mm")
        output = plan.to_phase5_commands()
        assert "Phase 5: Command Output" in output
        assert "```bash" in output
        assert "Step" in output
        assert "--json" in output

    def test_five_phase_report_complete(self):
        """Full five-phase report contains all phases."""
        plan = self.planner.plan("design a box 20x30x40mm")
        report = plan.to_five_phase_report()
        assert "Phase 1: Tool Selection" in report
        assert "Phase 2: Task Decomposition" in report
        assert "Phase 3: Coordinate & Dependency Calculation" in report
        assert "Phase 4: Dependency Validation" in report
        assert "Phase 5: Command Output" in report
        assert "Goal" in report
        assert "Total Tasks" in report

    def test_five_phase_report_in_plan_dict(self):
        """Plan.to_dict() includes five-phase metadata in tasks."""
        plan = self.planner.plan("design a box 20x30x40mm")
        d = plan.to_dict()
        for task_dict in d["tasks"]:
            assert "phase3_coords" in task_dict
            assert "phase3_dependency_elements" in task_dict
            assert "phase3_topology" in task_dict
            assert "phase5_comment" in task_dict

    def test_complex_request_five_phases(self):
        """Complex request generates valid five-phase output."""
        plan = self.planner.plan(
            "create a box 100x100x10 with a cylinder hole diameter 20, "
            "add fillet r=2, export step and stl"
        )
        report = plan.to_five_phase_report()
        # Should have tasks for: document, box, cylinder, fillet, export_step, export_stl, save
        assert len(plan.tasks) >= 5
        # Phase 1 should list multiple command groups
        phase1 = plan.to_phase1_tool_selection()
        assert "part" in phase1
        assert "export" in phase1
        # Phase 4 should pass validation
        phase4 = plan.to_phase4_dependency_validation()
        assert "PASS" in phase4

    def test_chinese_request_five_phases(self):
        """Chinese request generates valid five-phase output."""
        plan = self.planner.plan("设计一个 20x30x40 的长方体")
        report = plan.to_five_phase_report()
        assert "Phase 1" in report
        assert "Phase 5" in report
        assert len(plan.tasks) >= 5

    def test_task_phase5_comment_fallback(self):
        """Task without phase5_comment falls back to description."""
        plan = self.planner.plan("design a box")
        output = plan.to_phase5_commands()
        # All tasks should have comments (either phase5_comment or description)
        for t in plan.tasks:
            assert t.phase5_comment or t.description

    def test_empty_plan_five_phases(self):
        """Empty plan generates valid (empty) five-phase output."""
        plan = Plan(goal="empty test")
        report = plan.to_five_phase_report()
        assert "Phase 1" in report
        assert "Total Tasks: 0" in report or "Total Tasks**: 0" in report

    def test_phase_completeness_check_all_pass(self):
        """Completeness check passes when all 5 phases have valid data."""
        plan = self.planner.plan("design a box 20x30x40mm")
        report = plan.to_five_phase_report()
        assert "Phase Completeness Check" in report
        assert "ALL 5 PHASES COMPLETE" in report

    def test_phase_completeness_detected(self):
        """Completeness check catches missing phase 3 metadata."""
        plan = Plan(goal="missing coords")
        # Add a task without phase3_coords populated
        plan.tasks.append(Task(
            id="task_001",
            type=TaskType.PART_ADD,
            description="Add a box",
            command="fc",
            args=["--json", "part", "add", "box"],
            phase3_coords="",  # Empty — phase 3 incomplete
        ))
        report = plan._validate_phase_completeness()
        assert "Phase Completeness Check" in report
        # Should fail because there's a task with no coordinate metadata
        assert "INCOMPLETE" in report or "FAIL" in report

    def test_circular_dependency_detection(self):
        """Phase 4 detects circular dependencies."""
        plan = Plan(goal="circular deps")
        # Create tasks with circular deps: A depends on B, B depends on A
        plan.tasks.append(Task(id="task_a", type=TaskType.PART_ADD,
                                description="Task A", command="fc", args=["a"],
                                dependencies=["task_b"]))
        plan.tasks.append(Task(id="task_b", type=TaskType.PART_ADD,
                                description="Task B", command="fc", args=["b"],
                                dependencies=["task_a"]))
        output = plan.to_phase4_dependency_validation()
        assert "CYCLE DETECTED" in output
        assert "INVALID" in output

    def test_no_circular_deps_normal_plan(self):
        """Phase 4 reports no cycles for a normal plan."""
        plan = self.planner.plan("design a box 20x30x40mm")
        output = plan.to_phase4_dependency_validation()
        assert "No circular dependencies" in output
