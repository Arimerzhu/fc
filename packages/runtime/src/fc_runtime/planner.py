"""Planner — Natural language → Task tree decomposition.

Takes a natural language design request and breaks it into
executable Task objects that the Executor can run.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskType(str, Enum):
    """Types of tasks the agent can perform."""
    DOCUMENT_NEW = "document_new"
    DOCUMENT_OPEN = "document_open"
    DOCUMENT_SAVE = "document_save"
    PART_ADD = "part_add"
    PART_BOOLEAN = "part_boolean"
    PART_TRANSFORM = "part_transform"
    PART_MIRROR = "part_mirror"
    PART_SCALE = "part_scale"
    PART_FILLET = "part_fillet"
    PART_CHAMFER = "part_chamfer"
    SKETCH_NEW = "sketch_new"
    SKETCH_ADD_LINE = "sketch_add_line"
    SKETCH_ADD_CIRCLE = "sketch_add_circle"
    SKETCH_ADD_RECT = "sketch_add_rect"
    SKETCH_CONSTRAIN = "sketch_constrain"
    BODY_NEW = "body_new"
    BODY_PAD = "body_pad"
    BODY_POCKET = "body_pocket"
    BODY_REVOLUTION = "body_revolution"
    BODY_GROOVE = "body_groove"
    BODY_FILLET = "body_fillet"
    BODY_CHAMFER = "body_chamfer"
    EXPORT_STEP = "export_step"
    EXPORT_STL = "export_stl"
    EXPORT_PDF = "export_pdf"
    EXPORT_FCSTD = "export_fcstd"
    EXECUTE_CODE = "execute_code"
    CUSTOM = "custom"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


@dataclass
class Task:
    """A single executable task in the plan."""
    id: str
    type: TaskType
    description: str
    command: str  # The fc CLI command to execute
    args: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    retries: int = 0
    max_retries: int = 3
    # 五阶段执行流元数据
    phase3_coords: str = ""       # 坐标计算过程
    phase3_dependency_elements: list[str] = field(default_factory=list)  # 依赖的元素名称
    phase3_topology: str = ""      # 元素间拓扑关系
    phase5_comment: str = ""       # 命令注释说明

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "command": self.command,
            "args": self.args,
            "params": self.params,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retries": self.retries,
            "phase3_coords": self.phase3_coords,
            "phase3_dependency_elements": self.phase3_dependency_elements,
            "phase3_topology": self.phase3_topology,
            "phase5_comment": self.phase5_comment,
        }


@dataclass
class Plan:
    """A complete execution plan derived from a design request."""
    goal: str
    tasks: list[Task] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "status": self.status.value,
            "task_count": len(self.tasks),
            "tasks": [t.to_dict() for t in self.tasks],
            "context": self.context,
        }

    def get_task(self, task_id: str) -> Task | None:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def get_ready_tasks(self) -> list[Task]:
        """Get tasks whose dependencies are all completed."""
        completed = {t.id for t in self.tasks if t.status == TaskStatus.SUCCESS}
        ready = []
        for t in self.tasks:
            if t.status != TaskStatus.PENDING:
                continue
            if all(dep in completed for dep in t.dependencies):
                ready.append(t)
        return ready

    @property
    def progress(self) -> dict[str, int]:
        counts = {}
        for s in TaskStatus:
            counts[s.value] = sum(1 for t in self.tasks if t.status == s)
        return counts

    # ── 五阶段执行流输出方法 ──

    def to_phase1_tool_selection(self) -> str:
        """阶段 1: 工具选型 — 列出所有用到的命令组和命令"""
        from collections import Counter
        group_map = {
            TaskType.DOCUMENT_NEW: "document", TaskType.DOCUMENT_OPEN: "document",
            TaskType.DOCUMENT_SAVE: "document",
            TaskType.PART_ADD: "part", TaskType.PART_BOOLEAN: "part",
            TaskType.PART_TRANSFORM: "part", TaskType.PART_MIRROR: "part",
            TaskType.PART_SCALE: "part", TaskType.PART_FILLET: "part",
            TaskType.PART_CHAMFER: "part",
            TaskType.SKETCH_NEW: "sketch", TaskType.SKETCH_ADD_LINE: "sketch",
            TaskType.SKETCH_ADD_CIRCLE: "sketch", TaskType.SKETCH_ADD_RECT: "sketch",
            TaskType.SKETCH_CONSTRAIN: "sketch",
            TaskType.BODY_NEW: "body", TaskType.BODY_PAD: "body",
            TaskType.BODY_POCKET: "body", TaskType.BODY_REVOLUTION: "body",
            TaskType.BODY_GROOVE: "body", TaskType.BODY_FILLET: "body",
            TaskType.BODY_CHAMFER: "body",
            TaskType.EXPORT_STEP: "export", TaskType.EXPORT_STL: "export",
            TaskType.EXPORT_PDF: "export", TaskType.EXPORT_FCSTD: "export",
            TaskType.EXECUTE_CODE: "execute", TaskType.CUSTOM: "execute",
        }
        groups = Counter()
        commands = Counter()
        for t in self.tasks:
            g = group_map.get(t.type, "other")
            groups[g] += 1
            commands[t.type.value] += 1

        lines = ["## Phase 1: Tool Selection\n"]
        lines.append("### Command Groups")
        lines.append("| Group | Usage Count |")
        lines.append("|-------|-------------|")
        for g, c in sorted(groups.items()):
            lines.append(f"| {g} | {c} |")
        lines.append("")
        lines.append("### Commands")
        lines.append("| Command | Purpose |")
        lines.append("|---------|---------|")
        for cmd, c in sorted(commands.items()):
            desc = cmd.replace("_", " ").title()
            lines.append(f"| {cmd} | {desc} |")
        return "\n".join(lines)

    def to_phase2_task_decomposition(self) -> str:
        """阶段 2: 任务拆解 — 原子步骤列表"""
        lines = ["## Phase 2: Task Decomposition\n"]
        lines.append("| Step | Operation | Command | Dependencies |")
        lines.append("|------|-----------|---------|--------------|")
        for i, t in enumerate(self.tasks, 1):
            cmd_str = " ".join([t.command] + t.args[:3]) + ("..." if len(t.args) > 3 else "")
            deps = ", ".join(t.dependencies) if t.dependencies else "None"
            lines.append(f"| {i} | {t.description} | `{cmd_str}` | {deps} |")
        return "\n".join(lines)

    def to_phase3_coord_dependencies(self) -> str:
        """阶段 3: 坐标与依赖计算"""
        lines = ["## Phase 3: Coordinate & Dependency Calculation\n"]
        for i, t in enumerate(self.tasks, 1):
            lines.append(f"### Step {i}: {t.description}")
            # Coordinates
            if t.phase3_coords:
                lines.append(f"- **Coordinates**: {t.phase3_coords}")
            elif t.params:
                coord_parts = []
                for k in ("position", "length", "width", "height", "radius", "radius1", "radius2", "angle", "diameter", "size", "factor", "distance", "spacing", "count", "plane", "axis", "direction"):
                    if k in t.params:
                        coord_parts.append(f"{k}={t.params[k]}")
                if coord_parts:
                    lines.append(f"- **Coordinates**: {', '.join(coord_parts)}")
                else:
                    lines.append("- **Coordinates**: N/A (document/operation command)")
            else:
                lines.append("- **Coordinates**: N/A (document/operation command)")
            # Dependency elements
            if t.phase3_dependency_elements:
                lines.append(f"- **Dependency Elements**: {', '.join(t.phase3_dependency_elements)}")
            else:
                dep_ids = t.dependencies if t.dependencies else ["None"]
                lines.append(f"- **Dependency Elements**: {', '.join(dep_ids)}")
            # Topology
            if t.phase3_topology:
                lines.append(f"- **Topology**: {t.phase3_topology}")
            lines.append("")
        return "\n".join(lines)

    def to_phase4_dependency_validation(self) -> str:
        """阶段 4: 依赖校验 — 检查悬空引用 + 循环依赖"""
        lines = ["## Phase 4: Dependency Validation\n"]
        lines.append("| Step | Dependencies | Status | Notes |")
        lines.append("|------|-------------|--------|-------|")
        task_ids = {t.id for t in self.tasks}
        task_map = {t.id: t for t in self.tasks}
        all_valid = True

        # 4a: Dangling reference check
        dangling = []
        for i, t in enumerate(self.tasks, 1):
            if not t.dependencies:
                lines.append(f"| {i} | None | [OK] PASS | First step, no dependencies |")
                continue
            invalid = [d for d in t.dependencies if d not in task_ids]
            if invalid:
                lines.append(f"| {i} | {', '.join(t.dependencies)} | [FAIL] FAIL | Unknown: {', '.join(invalid)} |")
                dangling.extend(invalid)
                all_valid = False
            else:
                dep_descs = []
                for dep_id in t.dependencies:
                    dep_task = task_map.get(dep_id)
                    if dep_task:
                        dep_descs.append(f"{dep_id} ({dep_task.description})")
                lines.append(f"| {i} | {', '.join(t.dependencies)} | [OK] PASS | {', '.join(dep_descs)} |")

        # 4b: Circular dependency detection (DFS)
        lines.append("")
        lines.append("### Circular Dependency Check")
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {t.id: WHITE for t in self.tasks}
        cycle_path = []
        has_cycle = False

        def dfs(node_id: str) -> bool:
            nonlocal has_cycle
            color[node_id] = GRAY
            cycle_path.append(node_id)
            task = task_map.get(node_id)
            if task:
                for dep_id in task.dependencies:
                    if dep_id not in color:
                        continue  # dangling already reported
                    if color[dep_id] == GRAY:
                        # Found cycle
                        cycle_start = cycle_path.index(dep_id)
                        cycle = " -> ".join(cycle_path[cycle_start:] + [dep_id])
                        lines.append(f"- [FAIL] CYCLE DETECTED: {cycle}")
                        has_cycle = True
                        return True
                    if color[dep_id] == WHITE:
                        if dfs(dep_id):
                            return True
            cycle_path.pop()
            color[node_id] = BLACK
            return False

        for t in self.tasks:
            if color[t.id] == WHITE:
                dfs(t.id)

        if not has_cycle:
            lines.append("- [OK] No circular dependencies detected")

        lines.append("")
        if all_valid and not has_cycle:
            lines.append("**Result**: ALL VALID — No dangling references. No circular dependencies.")
        else:
            issues = []
            if dangling:
                issues.append(f"dangling references: {', '.join(set(dangling))}")
            if has_cycle:
                issues.append("circular dependencies detected")
            lines.append(f"**Result**: INVALID — {'; '.join(issues)}. Must fix before execution.")
        return "\n".join(lines)

    def to_phase5_commands(self) -> str:
        """阶段 5: 命令输出"""
        lines = ["## Phase 5: Command Output\n"]
        lines.append("```bash")
        for i, t in enumerate(self.tasks, 1):
            comment = t.phase5_comment or t.description
            lines.append(f"# Step {i}: {comment}")
            cmd_str = " ".join([t.command] + t.args)
            lines.append(f"{cmd_str}")
            lines.append("")
        lines.append("```")
        return "\n".join(lines)

    def to_five_phase_report(self) -> str:
        """生成完整的五阶段执行流报告，带阶段完整性校验"""
        parts = [
            f"# Five-Phase Execution Plan",
            f"**Goal**: {self.goal}",
            f"**Total Tasks**: {len(self.tasks)}",
            "",
            self.to_phase1_tool_selection(),
            "",
            self.to_phase2_task_decomposition(),
            "",
            self.to_phase3_coord_dependencies(),
            "",
            self.to_phase4_dependency_validation(),
            "",
            self.to_phase5_commands(),
            "",
            self._validate_phase_completeness(),
        ]
        return "\n".join(parts)

    def _validate_phase_completeness(self) -> str:
        """校验五个阶段的完整性 — 跳过任何一步都算失败"""
        lines = ["---\n", "## Phase Completeness Check\n"]
        checks = []

        # Phase 1: Tool selection should list at least one command group
        has_tasks = len(self.tasks) > 0
        checks.append(("Phase 1: Tool Selection", has_tasks, "No tasks generated"))

        # Phase 2: Task decomposition should have all tasks with descriptions
        all_described = all(t.description for t in self.tasks)
        checks.append(("Phase 2: Task Decomposition", all_described, "Some tasks lack descriptions"))

        # Phase 3: Coordinate calculation
        has_coords = any(t.phase3_coords or t.params for t in self.tasks)
        checks.append(("Phase 3: Coordinate & Dependency", has_coords,
                       "No coordinate metadata found — populate phase3_coords / params"))

        # Phase 4: Dependencies should be validated
        task_ids = {t.id for t in self.tasks}
        deps_valid = all(
            all(d in task_ids for d in t.dependencies) for t in self.tasks
        )
        checks.append(("Phase 4: Dependency Validation", deps_valid,
                       "Dangling dependency references detected"))

        # Phase 5: Commands should be non-empty
        has_commands = all(t.command and t.args for t in self.tasks if t.type not in (
            "document_save", "document_new", "document_open",
        ) or True)  # All tasks must have command field
        all_have_commands = all(t.command for t in self.tasks)
        checks.append(("Phase 5: Command Output", all_have_commands,
                       "Some tasks lack command field"))

        all_pass = True
        for name, passed, fail_msg in checks:
            status = "[OK] PASS" if passed else "[FAIL] FAIL"
            if not passed:
                all_pass = False
            lines.append(f"- {status} - {name}")
            if not passed:
                lines.append(f"         [WARN] {fail_msg}")

        lines.append("")
        if all_pass:
            lines.append("**Overall: ALL 5 PHASES COMPLETE [OK]**")
        else:
            lines.append("**Overall: INCOMPLETE - fix failed phases before execution [FAIL]**")
        return "\n".join(lines)


class Planner:
    """Decomposes natural language design requests into executable plans.

    Uses pattern matching and keyword extraction to identify:
    - What parts to create (box, cylinder, gear, flange, etc.)
    - What operations to perform (boolean, fillet, chamfer, etc.)
    - What exports to produce (STEP, STL, PDF, etc.)
    - Dependencies between tasks
    """

    # Known design templates
    TEMPLATES = {
        "box": {
            "keywords": ["box", "立方体", "长方体", "方块"],
            "task_type": TaskType.PART_ADD,
            "defaults": {"part_type": "box", "length": 10, "width": 10, "height": 10},
        },
        "cylinder": {
            "keywords": ["cylinder", "圆柱", "圆筒", "轴"],
            "task_type": TaskType.PART_ADD,
            "defaults": {"part_type": "cylinder", "radius": 5, "height": 10},
        },
        "sphere": {
            "keywords": ["sphere", "球", "球体"],
            "task_type": TaskType.PART_ADD,
            "defaults": {"part_type": "sphere", "radius": 5},
        },
        "cone": {
            "keywords": ["cone", "圆锥", "锥体"],
            "task_type": TaskType.PART_ADD,
            "defaults": {"part_type": "cone", "radius1": 5, "radius2": 0, "height": 10},
        },
        "flange": {
            "keywords": ["flange", "法兰", "法兰盘"],
            "task_type": TaskType.CUSTOM,
            "defaults": {},
        },
        "gear": {
            "keywords": ["gear", "齿轮"],
            "task_type": TaskType.CUSTOM,
            "defaults": {},
        },
        "shaft": {
            "keywords": ["shaft", "轴", "转轴"],
            "task_type": TaskType.CUSTOM,
            "defaults": {},
        },
        "housing": {
            "keywords": ["housing", "壳体", "外壳", "机箱"],
            "task_type": TaskType.CUSTOM,
            "defaults": {},
        },
        "bolt": {
            "keywords": ["bolt", "螺栓", "螺钉", "螺丝"],
            "task_type": TaskType.CUSTOM,
            "defaults": {},
        },
        "nut": {
            "keywords": ["nut", "螺母"],
            "task_type": TaskType.CUSTOM,
            "defaults": {},
        },
        "bearing": {
            "keywords": ["bearing", "轴承"],
            "task_type": TaskType.CUSTOM,
            "defaults": {},
        },
        "reducer": {
            "keywords": ["reducer", "减速器", "减速机", "齿轮箱"],
            "task_type": TaskType.CUSTOM,
            "defaults": {},
        },
    }

    EXPORT_FORMATS = {
        "step": TaskType.EXPORT_STEP,
        "stl": TaskType.EXPORT_STL,
        "pdf": TaskType.EXPORT_PDF,
        "fcstd": TaskType.EXPORT_FCSTD,
    }

    def __init__(self):
        self._task_counter = 0

    def _next_id(self) -> str:
        self._task_counter += 1
        return f"task_{self._task_counter:03d}"

    def plan(self, request: str, project_path: str | None = None,
             session: str | None = None) -> Plan:
        """Generate an execution plan from a natural language request.

        Args:
            request: Natural language design request (Chinese or English)
            project_path: Optional path to a .FCStd file for session persistence.
                          If provided, all tasks include --project flag.
            session: Optional FreeCAD 持久化会话名。如果提供，
                     plan.context 记录该会话，Executor 通过 --session 路由到此 GUI 实例。

        Returns:
            A Plan with ordered tasks ready for execution, including five-phase metadata.
        """
        self._task_counter = 0
        plan = Plan(goal=request)
        if session:
            plan.context["session"] = session
        request_lower = request.lower()

        # Build the project flag for session persistence
        project_flag = ["--project", project_path] if project_path else []

        # Track element names for dependency resolution
        element_names: dict[str, str] = {}  # part_name -> task_id

        # Step 1: Create document
        doc_name = self._extract_document_name(request)
        plan.tasks.append(Task(
            id=self._next_id(),
            type=TaskType.DOCUMENT_NEW,
            description=f"Create document '{doc_name}'",
            command="fc",
            args=project_flag + ["--json", "document", "new", "--name", doc_name],
            phase3_coords="N/A (document operation)",
            phase3_dependency_elements=[],
            phase3_topology="N/A",
            phase5_comment=f"Create new FreeCAD document '{doc_name}'",
        ))

        # Step 2: Detect parts to create
        parts = self._detect_parts(request)
        last_part_id = None
        last_part_name = None

        for part in parts:
            task = self._create_part_task(part, project_flag)
            task.dependencies = [plan.tasks[0].id]  # Depends on document creation
            # Phase 3 metadata
            part_name = part.get("name", "unknown").capitalize()
            element_names[part_name] = task.id
            coord_parts = []
            if "length" in part:
                coord_parts.append(f"Length={part['length']}")
            if "width" in part:
                coord_parts.append(f"Width={part['width']}")
            if "height" in part:
                coord_parts.append(f"Height={part['height']}")
            if "radius" in part:
                coord_parts.append(f"Radius={part['radius']}")
            task.phase3_coords = ", ".join(coord_parts) if coord_parts else "Default dimensions"
            task.phase3_dependency_elements = [doc_name]
            task.phase3_topology = f"Base geometry in world coordinates"
            task.phase5_comment = f"Add {part.get('part_type', 'box')}: {part_name}"
            plan.tasks.append(task)
            last_part_id = task.id
            last_part_name = part_name

        # Step 3: Detect operations
        operations = self._detect_operations(request)
        for op in operations:
            task = self._create_operation_task(op, project_flag)
            if last_part_id:
                task.dependencies.append(last_part_id)
            # Phase 3 metadata
            op_type = op.get("type", "unknown")
            if op_type == "fillet":
                task.phase3_coords = f"radius={op.get('radius', 1.0)}mm"
                task.phase3_topology = f"Fillet on edges of {last_part_name}"
            elif op_type == "chamfer":
                task.phase3_coords = f"size={op.get('size', 1.0)}mm"
                task.phase3_topology = f"Chamfer on edges of {last_part_name}"
            elif op_type == "boolean":
                task.phase3_coords = f"operation={op.get('operation', 'fuse')}"
                task.phase3_topology = f"Boolean {op.get('operation', 'fuse')} with {last_part_name}"
            elif op_type == "mirror":
                task.phase3_coords = f"plane={op.get('plane', 'XY')}"
                task.phase3_topology = f"Mirror {last_part_name} across {op.get('plane', 'XY')} plane"
            else:
                task.phase3_coords = str(op)
                task.phase3_topology = f"{op_type} operation on {last_part_name}"
            task.phase3_dependency_elements = [last_part_name] if last_part_name else []
            task.phase5_comment = f"{op_type.capitalize()} operation"
            plan.tasks.append(task)

        # Step 4: Detect exports
        exports = self._detect_exports(request)
        for fmt in exports:
            task = self._create_export_task(fmt, project_flag)
            if last_part_id:
                task.dependencies.append(last_part_id)
            # Phase 3 metadata
            task.phase3_coords = "N/A (export operation)"
            task.phase3_dependency_elements = [last_part_name] if last_part_name else []
            task.phase3_topology = "N/A"
            task.phase5_comment = f"Export to {fmt.upper()}"
            plan.tasks.append(task)

        # Step 5: If no specific parts detected, create a default box
        if not parts and not operations:
            default_task = Task(
                id=self._next_id(),
                type=TaskType.PART_ADD,
                description="Create default box (10x10x10mm)",
                command="fc",
                args=project_flag + ["--json", "part", "add", "box", "--name", "Box",
                      "--param", "Length=10", "--param", "Width=10",
                      "--param", "Height=10"],
                dependencies=[plan.tasks[0].id],
                phase3_coords="Length=10, Width=10, Height=10 (default)",
                phase3_dependency_elements=[doc_name],
                phase3_topology="Base geometry at world origin",
                phase5_comment="Create default box (no specific parts detected)",
            )
            plan.tasks.append(default_task)
            last_part_id = default_task.id
            last_part_name = "Box"

        # Step 6: Always add FCStd save at the end
        all_task_ids = [t.id for t in plan.tasks if t.type != TaskType.DOCUMENT_SAVE]
        plan.tasks.append(Task(
            id=self._next_id(),
            type=TaskType.DOCUMENT_SAVE,
            description="Save document",
            command="fc",
            args=project_flag + ["--json", "document", "save", "--output", "output.FCStd"],
            dependencies=all_task_ids[-1:] if all_task_ids else [],
            phase3_coords="N/A (save operation)",
            phase3_dependency_elements=[last_part_name] if last_part_name else [],
            phase3_topology="N/A",
            phase5_comment="Save document as .FCStd",
        ))

        return plan

    def _extract_document_name(self, request: str) -> str:
        """Extract a document name from the request."""
        # Try to find quoted text
        match = re.search(r'"([^"]+)"', request)
        if match:
            return match.group(1).replace(" ", "_")
        # Try to find the main noun phrase
        for template in self.TEMPLATES.values():
            for kw in template["keywords"]:
                if kw in request.lower():
                    return kw.capitalize()
        return "Design"

    def _detect_parts(self, request: str) -> list[dict]:
        """Detect what parts to create from the request."""
        parts = []
        request_lower = request.lower()

        for name, template in self.TEMPLATES.items():
            for kw in template["keywords"]:
                if kw in request_lower:
                    part = {"name": name, **template["defaults"]}
                    # Extract dimensions
                    dims = self._extract_dimensions(request)
                    if dims:
                        part.update(dims)
                    parts.append(part)
                    break  # Only add each part type once

        return parts

    def _extract_dimensions(self, request: str) -> dict[str, float]:
        """Extract dimension values from the request."""
        dims = {}

        # Match patterns like: 10x20x30, 10*20*30, 10,20,30
        dim_match = re.search(r'(\d+\.?\d*)\s*[xX*×,]\s*(\d+\.?\d*)\s*[xX*×,]\s*(\d+\.?\d*)', request)
        if dim_match:
            dims["length"] = float(dim_match.group(1))
            dims["width"] = float(dim_match.group(2))
            dims["height"] = float(dim_match.group(3))
            return dims

        # Match diameter: D=50, 直径50, dia 50
        dia_match = re.search(r'(?:d|diameter|直径|Φ)\s*[=]?\s*(\d+\.?\d*)', request, re.IGNORECASE)
        if dia_match:
            dims["radius"] = float(dia_match.group(1)) / 2

        # Match single dimension: 长10, 宽20, 高30
        l_match = re.search(r'(?:长|length|L)\s*[=]?\s*(\d+\.?\d*)', request, re.IGNORECASE)
        if l_match:
            dims["length"] = float(l_match.group(1))
        w_match = re.search(r'(?:宽|width|W)\s*[=]?\s*(\d+\.?\d*)', request, re.IGNORECASE)
        if w_match:
            dims["width"] = float(w_match.group(1))
        h_match = re.search(r'(?:高|height|H)\s*[=]?\s*(\d+\.?\d*)', request, re.IGNORECASE)
        if h_match:
            dims["height"] = float(h_match.group(1))

        return dims

    def _detect_operations(self, request: str) -> list[dict]:
        """Detect what operations to perform."""
        ops = []
        request_lower = request.lower()

        # Boolean operations
        if any(kw in request_lower for kw in ["boolean", "布尔", "并集", "交集", "差集", "合并", "切割"]):
            ops.append({"type": "boolean", "operation": "fuse"})

        # Fillet
        if any(kw in request_lower for kw in ["fillet", "圆角", "倒圆"]):
            radius = self._extract_radius(request)
            ops.append({"type": "fillet", "radius": radius})

        # Chamfer
        if any(kw in request_lower for kw in ["chamfer", "倒角"]):
            size = self._extract_chamfer_size(request)
            ops.append({"type": "chamfer", "size": size})

        # Mirror
        if any(kw in request_lower for kw in ["mirror", "镜像", "对称"]):
            ops.append({"type": "mirror", "plane": "XY"})

        # Array/Pattern
        if any(kw in request_lower for kw in ["array", "阵列", "排列"]):
            count = self._extract_array_count(request)
            ops.append({"type": "array", "count": count})

        return ops

    def _extract_radius(self, request: str) -> float:
        match = re.search(r'(?:r|radius|半径)\s*[=]?\s*(\d+\.?\d*)', request, re.IGNORECASE)
        return float(match.group(1)) if match else 1.0

    def _extract_chamfer_size(self, request: str) -> float:
        match = re.search(r'(?:s|size|大小|尺寸)\s*[=]?\s*(\d+\.?\d*)', request, re.IGNORECASE)
        return float(match.group(1)) if match else 1.0

    def _extract_array_count(self, request: str) -> int:
        match = re.search(r'(\d+)\s*(?:x|X|个|件)', request)
        return int(match.group(1)) if match else 4

    def _detect_exports(self, request: str) -> list[str]:
        """Detect what export formats are requested."""
        exports = []
        request_lower = request.lower()

        for fmt in ["step", "stl", "pdf", "fcstd", "obj", "dxf", "svg"]:
            if fmt in request_lower:
                exports.append(fmt)

        # Default exports if none specified
        if not exports:
            exports = ["step", "stl"]

        return exports

    def _create_part_task(self, part: dict, project_flag: list[str] | None = None) -> Task:
        """Create a task for adding a part."""
        project_flag = project_flag or []
        name = part["name"]
        task_type = part.get("task_type", TaskType.PART_ADD)

        if task_type == TaskType.CUSTOM:
            return Task(
                id=self._next_id(),
                type=TaskType.CUSTOM,
                description=f"Create custom part: {name}",
                command="fc",
                args=["execute", "code", "--json"],
                params={"part_name": name, "part": part},
            )

        # Standard primitive
        part_type = part.get("part_type", "box")
        args = project_flag + ["--json", "part", "add", part_type, "--name", name.capitalize()]

        if "length" in part:
            args.extend(["--param", f"Length={part['length']}"])
        if "width" in part:
            args.extend(["--param", f"Width={part['width']}"])
        if "height" in part:
            args.extend(["--param", f"Height={part['height']}"])
        if "radius" in part:
            args.extend(["--param", f"Radius={part['radius']}"])
        if "radius1" in part:
            args.extend(["--param", f"Radius1={part['radius1']}"])
        if "radius2" in part:
            args.extend(["--param", f"Radius2={part['radius2']}"])

        return Task(
            id=self._next_id(),
            type=task_type,
            description=f"Add {part_type}: {name}",
            command="fc",
            args=args,
            params=part,
        )

    def _create_operation_task(self, op: dict, project_flag: list[str] | None = None) -> Task:
        """Create a task for an operation."""
        project_flag = project_flag or []
        op_type = op["type"]

        if op_type == "fillet":
            return Task(
                id=self._next_id(),
                type=TaskType.PART_FILLET,
                description=f"Fillet (r={op.get('radius', 1.0)})",
                command="fc",
                args=project_flag + ["--json", "part", "fillet-3d", "--radius", str(op.get("radius", 1.0))],
                params=op,
            )
        elif op_type == "chamfer":
            return Task(
                id=self._next_id(),
                type=TaskType.PART_CHAMFER,
                description=f"Chamfer (size={op.get('size', 1.0)})",
                command="fc",
                args=project_flag + ["--json", "part", "chamfer-3d", "--size", str(op.get("size", 1.0))],
                params=op,
            )
        elif op_type == "mirror":
            return Task(
                id=self._next_id(),
                type=TaskType.PART_MIRROR,
                description=f"Mirror across {op.get('plane', 'XY')}",
                command="fc",
                args=project_flag + ["--json", "part", "mirror", "--plane", op.get("plane", "XY")],
                params=op,
            )
        elif op_type == "boolean":
            return Task(
                id=self._next_id(),
                type=TaskType.PART_BOOLEAN,
                description=f"Boolean {op.get('operation', 'fuse')}",
                command="fc",
                args=project_flag + ["--json", "part", "boolean", op.get("operation", "fuse")],
                params=op,
            )
        else:
            return Task(
                id=self._next_id(),
                type=TaskType.CUSTOM,
                description=f"Operation: {op_type}",
                command="fc",
                args=project_flag + ["--json", "execute", "code"],
                params=op,
            )

    def _create_export_task(self, fmt: str, project_flag: list[str] | None = None) -> Task:
        """Create a task for exporting."""
        project_flag = project_flag or []
        task_type = self.EXPORT_FORMATS.get(fmt, TaskType.EXPORT_STEP)
        output_file = f"output.{fmt}"

        return Task(
            id=self._next_id(),
            type=task_type,
            description=f"Export to {fmt.upper()}",
            command="fc",
            args=project_flag + ["--json", "export", fmt, output_file, "--overwrite"],
            params={"format": fmt, "output": output_file},
        )
