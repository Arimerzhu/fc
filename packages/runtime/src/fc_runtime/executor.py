"""Executor — Runs planned tasks via fc CLI commands.

Handles subprocess execution, output parsing, error detection,
progress tracking, and context injection (element summary feedback).
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fc_core.types import ToolResponse
from fc_runtime.planner import TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class ElementSummary:
    """Summary of a created element for context injection."""
    name: str
    type: str
    task_id: str
    command: str
    params: dict[str, Any] = field(default_factory=dict)
    position: str = ""
    dimensions: dict[str, float] = field(default_factory=dict)

    def to_context_line(self) -> str:
        """Format as a single context line for AI consumption."""
        parts = [f"{self.name} ({self.type})"]
        if self.position:
            parts.append(f"position={self.position}")
        if self.dimensions:
            dim_str = "x".join(str(v) for v in self.dimensions.values())
            parts.append(f"dimensions={dim_str}")
        return ", ".join(parts)


@dataclass
class BatchContext:
    """Context accumulated from a batch of executed tasks."""
    batch_number: int
    elements: list[ElementSummary] = field(default_factory=list)
    commands_executed: list[str] = field(default_factory=list)
    success_count: int = 0
    fail_count: int = 0

    def to_injection_text(self) -> str:
        """Generate context injection text for AI feedback."""
        lines = [
            f"## Batch {self.batch_number} Execution Results",
            f"",
            f"**Status**: {self.success_count} succeeded, {self.fail_count} failed",
            f"",
        ]
        if self.elements:
            lines.append("**Created Elements:**")
            for elem in self.elements:
                lines.append(f"- {elem.to_context_line()}")
            lines.append("")
        if self.commands_executed:
            lines.append("**Executed Commands:**")
            for i, cmd in enumerate(self.commands_executed, 1):
                lines.append(f"{i}. `{cmd}`")
            lines.append("")
        return "\n".join(lines)

    def get_element_names(self) -> list[str]:
        """Return list of all created element names."""
        return [e.name for e in self.elements]


@dataclass
class TaskResult:
    """Result of executing a single task."""
    task_id: str
    success: bool
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0

    @property
    def failed(self) -> bool:
        return not self.success

    @classmethod
    def from_subprocess(cls, task_id: str, result: subprocess.CompletedProcess,
                        duration_ms: float = 0.0) -> TaskResult:
        """Create a TaskResult from a CompletedProcess."""
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""

        # Try to parse JSON output
        data = {}
        if stdout:
            try:
                data = json.loads(stdout)
            except json.JSONDecodeError:
                # Look for JSON in the output
                for line in stdout.splitlines():
                    line = line.strip()
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            data = json.loads(line)
                            break
                        except json.JSONDecodeError:
                            continue

        success = result.returncode == 0
        error_msg = ""
        if not success:
            if isinstance(data, dict) and "error" in data:
                error_msg = data["error"].get("message", data["error"].get("code", stderr))
            elif isinstance(data, dict) and "message" in data:
                error_msg = data["message"]
            else:
                error_msg = stderr or stdout or f"Command failed (exit code {result.returncode})"

        return cls(
            task_id=task_id,
            success=success,
            returncode=result.returncode,
            stdout=stdout,
            stderr=stderr,
            data=data,
            error=error_msg,
            duration_ms=duration_ms,
        )


class Executor:
    """Executes planned tasks by running fc CLI commands.

    Supports context injection: after each batch of 5-10 commands,
    generates an element summary that can be fed back to the Planner
    for subsequent task reference validation.
    """

    def __init__(self, fc_path: str = "fc", timeout: int = 120,
                 working_dir: str | None = None, backend: str = "headless",
                 dry_run: bool = False, batch_size: int = 10,
                 session: str | None = None):
        self._fc_path = fc_path
        self._timeout = timeout
        self._working_dir = working_dir
        self._backend = backend
        self._dry_run = dry_run
        self._batch_size = batch_size
        self._session = session  # 持久化会话名，通过 --session X 路由到特定 FreeCAD GUI 实例
        self._results: list[TaskResult] = []
        self._dry_run_log: list[str] = []
        # Context injection state
        self._context_batches: list[BatchContext] = []
        self._current_batch: BatchContext | None = None
        self._all_elements: dict[str, ElementSummary] = {}  # name -> summary
        self._element_name_pattern = re.compile(
            r'["\']([A-Za-z][A-Za-z0-9_]*)["\']'  # quoted names
            r'|name[=:]\s*["\']?([A-Za-z][A-Za-z0-9_]*)["\']?'  # name=XXX
            r'|"name":\s*"([A-Za-z][A-Za-z0-9_]*)"'  # JSON "name": "XXX"
        )

    @property
    def results(self) -> list[TaskResult]:
        return list(self._results)

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    @dry_run.setter
    def dry_run(self, value: bool) -> None:
        self._dry_run = value

    @property
    def dry_run_log(self) -> list[str]:
        return list(self._dry_run_log)

    @property
    def context_batches(self) -> list[BatchContext]:
        return list(self._context_batches)

    @property
    def all_elements(self) -> dict[str, ElementSummary]:
        return dict(self._all_elements)

    def execute_task(self, task) -> TaskResult:
        """Execute a single task.

        Args:
            task: A Task object from the planner

        Returns:
            TaskResult with execution outcome
        """
        import time

        logger.info(f"Executing: {task.description}")
        print(f"  > {task.description}")

        start = time.time()

        # Build command
        cmd = [self._fc_path] + task.args
        if self._session:
            # session 优先：路由到指定 FreeCAD GUI 实例的 RPC 后端
            cmd.extend(["--session", self._session])
        elif self._backend == "rpc":
            cmd.extend(["--backend", "rpc"])

        # Dry-run mode: print command and return simulated success
        if self._dry_run:
            cmd_str = " ".join(cmd)
            logger.info(f"[DRY RUN] Would execute: {cmd_str}")
            print(f"  > [DRY RUN] {cmd_str}")
            self._dry_run_log.append(cmd_str)
            task.status = TaskStatus.SUCCESS
            task.result = {"dry_run": True, "command": cmd_str}
            task_result = TaskResult(
                task_id=task.id,
                success=True,
                stdout='{"dry_run": true}',
                data={"dry_run": True, "command": cmd_str},
                duration_ms=0.0,
            )
            self._results.append(task_result)
            return task_result

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=self._working_dir,
            )
            duration = (time.time() - start) * 1000
            task_result = TaskResult.from_subprocess(task.id, result, duration)

        except subprocess.TimeoutExpired:
            duration = (time.time() - start) * 1000
            task_result = TaskResult(
                task_id=task.id,
                success=False,
                error=f"Task timed out after {self._timeout}s",
                duration_ms=duration,
            )
        except FileNotFoundError:
            duration = (time.time() - start) * 1000
            task_result = TaskResult(
                task_id=task.id,
                success=False,
                error=f"fc command not found: {self._fc_path}. Is fc installed?",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            task_result = TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                duration_ms=duration,
            )

        # Update task status
        if task_result.success:
            task.status = TaskStatus.SUCCESS
            task.result = task_result.data
            print(f"    [OK] Done ({task_result.duration_ms:.0f}ms)")
        else:
            task.status = TaskStatus.FAILED
            task.error = task_result.error
            task.retries += 1
            print(f"    [FAIL] Failed: {task_result.error}")

        self._results.append(task_result)
        return task_result

    def execute_plan(self, plan, corrector=None) -> list[TaskResult]:
        """Execute all tasks in a plan, respecting dependencies.

        Args:
            plan: A Plan object from the planner
            corrector: Optional Corrector for retrying failed tasks

        Returns:
            List of TaskResult for all executed tasks
        """
        plan.status = TaskStatus.RUNNING
        self._results = []

        print(f"\n{'='*60}")
        print(f"Executing plan: {plan.goal}")
        print(f"Tasks: {len(plan.tasks)}")
        print(f"{'='*60}\n")

        max_iterations = len(plan.tasks) * 3  # Allow for retries
        iteration = 0
        batch_number = 0
        tasks_in_current_batch = 0

        while iteration < max_iterations:
            ready = plan.get_ready_tasks()
            if not ready:
                break

            # Start a new batch if this is the first batch or batch_size reached
            if tasks_in_current_batch == 0:
                batch_number += 1
                self._start_batch(batch_number)

            for task in ready:
                task.status = TaskStatus.RUNNING
                result = self.execute_task(task)
                self._record_task_result(task, result)
                tasks_in_current_batch += 1

                if result.failed and corrector and task.retries < task.max_retries:
                    corrected = corrector.correct(task, result)
                    if corrected:
                        print(f"    [RETRY] Retrying (attempt {task.retries}/{task.max_retries})")
                        task.status = TaskStatus.RETRYING
                        retry_result = self.execute_task(task)
                        self._record_task_result(task, retry_result)
                        if retry_result.success:
                            task.status = TaskStatus.SUCCESS

                # Finalize batch when batch_size reached
                if tasks_in_current_batch >= self._batch_size:
                    batch = self._finalize_batch()
                    if batch:
                        print(f"\n{batch.to_injection_text()}")
                    tasks_in_current_batch = 0

            iteration += 1

        # Finalize any remaining tasks in the last batch
        if tasks_in_current_batch > 0:
            batch = self._finalize_batch()
            if batch:
                print(f"\n{batch.to_injection_text()}")
                tasks_in_current_batch = 0

        # Set final plan status
        if all(t.status == "success" for t in plan.tasks):
            plan.status = TaskStatus.SUCCESS
        elif any(t.status == "failed" for t in plan.tasks):
            plan.status = TaskStatus.FAILED

        return self._results

    def execute_direct(self, command: str, args: list[str] | None = None) -> TaskResult:
        """Execute a direct CLI command (not from a plan).

        Args:
            command: The command string to execute
            args: Optional additional arguments

        Returns:
            TaskResult with execution outcome
        """
        import time

        cmd_parts = command.split()
        if args:
            cmd_parts.extend(args)

        cmd = [self._fc_path] + cmd_parts
        if self._session:
            cmd.extend(["--session", self._session])
        elif self._backend == "rpc":
            cmd.extend(["--backend", "rpc"])

        # Dry-run mode
        if self._dry_run:
            cmd_str = " ".join(cmd)
            logger.info(f"[DRY RUN] Would execute: {cmd_str}")
            print(f"  > [DRY RUN] {cmd_str}")
            self._dry_run_log.append(cmd_str)
            return TaskResult(
                task_id="direct",
                success=True,
                stdout='{"dry_run": true}',
                data={"dry_run": True, "command": cmd_str},
                duration_ms=0.0,
            )

        start = time.time()
    # ── Context Injection Methods ──

    def _extract_element_from_result(self, task, task_result: TaskResult) -> ElementSummary | None:
        """Extract element info from a successful task result for context tracking."""
        data = task_result.data
        if not isinstance(data, dict):
            return None

        name = data.get("name", "")
        if not name:
            # Try to extract from task args
            for i, arg in enumerate(task.args):
                if arg == "--name" and i + 1 < len(task.args):
                    name = task.args[i + 1]
                    break

        if not name:
            return None

        type_id = data.get("type_id", data.get("type", task.type.value))
        # Clean up type_id (e.g., "Part::Box" -> "Box")
        if "::" in type_id:
            type_id = type_id.split("::")[-1]

        # Extract dimensions from params or data
        dimensions = {}
        for dim_key in ("Length", "Width", "Height", "Radius", "Radius1", "Radius2"):
            if dim_key in data:
                dimensions[dim_key.lower()] = float(data[dim_key])
            elif dim_key.lower() in task.params:
                dimensions[dim_key.lower()] = float(task.params[dim_key.lower()])

        # Extract position
        position = ""
        if "position" in data:
            pos = data["position"]
            if isinstance(pos, (list, tuple)):
                position = ",".join(str(v) for v in pos)
            else:
                position = str(pos)
        elif "Placement" in data:
            pos = data["Placement"].get("Base", {})
            if isinstance(pos, dict):
                position = f"{pos.get('x', 0)},{pos.get('y', 0)},{pos.get('z', 0)}"

        return ElementSummary(
            name=name,
            type=type_id,
            task_id=task.id,
            command=task.command,
            params=dict(task.params),
            position=position,
            dimensions=dimensions,
        )

    def _start_batch(self, batch_number: int) -> None:
        """Initialize a new batch context."""
        self._current_batch = BatchContext(batch_number=batch_number)

    def _record_task_result(self, task, task_result: TaskResult) -> None:
        """Record a task result into the current batch context."""
        if self._current_batch is None:
            return

        cmd_str = " ".join([task.command] + task.args)
        self._current_batch.commands_executed.append(cmd_str)

        if task_result.success:
            self._current_batch.success_count += 1
            element = self._extract_element_from_result(task, task_result)
            if element:
                self._current_batch.elements.append(element)
                self._all_elements[element.name] = element
        else:
            self._current_batch.fail_count += 1

    def _finalize_batch(self) -> BatchContext | None:
        """Finalize the current batch and add to history."""
        if self._current_batch is None:
            return None
        batch = self._current_batch
        self._context_batches.append(batch)
        self._current_batch = None
        return batch

    def get_context_injection(self) -> str:
        """Generate full context injection text from all completed batches."""
        if not self._context_batches:
            return "No execution context available yet."
        parts = ["# Execution Context Summary\n"]
        for batch in self._context_batches:
            parts.append(batch.to_injection_text())
        # Add cumulative element list
        if self._all_elements:
            parts.append("## All Created Elements (Cumulative)")
            parts.append("| Name | Type | Position |")
            parts.append("|------|------|----------|")
            for name, elem in sorted(self._all_elements.items()):
                pos = elem.position or "origin"
                parts.append(f"| {name} | {elem.type} | {pos} |")
            parts.append("")
        return "\n".join(parts)

    def validate_element_reference(self, element_name: str) -> bool:
        """Check if an element name has been created (available for reference)."""
        return element_name in self._all_elements

    def get_available_elements(self) -> list[str]:
        """Get list of all element names available for reference."""
        return sorted(self._all_elements.keys())
