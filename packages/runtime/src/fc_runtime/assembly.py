"""P3.4 — 多零件装配

核心数据结构：
  AssemblyPart        — 装配中的单个零件实例（含局部坐标/旋转）
  AssemblyConstraint  — 两个零件之间的约束（贴合/对齐/同轴）
  AssemblyDesign      — 完整的装配方案（零件列表 + 约束列表）
  AssemblyAgent       — 将零件描述 → AssemblyDesign 的转换 Agent
  AssemblyExecutor    — 将 AssemblyDesign 转换成 FreeCAD 脚本/CLI 命令

典型拓扑（一个简单的电机安装座）：
  Part(base_plate)  ← coaxial_fit  ← Part(bolt_m6x16)
  Part(bracket)     ← face_contact ← Part(base_plate)
  Part(motor_shaft) ← coaxial_fit  ← Part(bracket_hole)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fc_runtime.agent_logging import AgentLogger, get_logger
from fc_runtime.agent_schemas import (
    CADModelingOutput,
    RequirementDocument,
    PartType,
)


# ── 约束类型 ───────────────────────────

class ConstraintType(str, Enum):
    """工程装配约束类型。"""
    FACE_CONTACT = "face_contact"  # 面贴合（face1 + face2 贴合）
    COAXIAL = "coaxial"              # 同轴（两个圆柱面中心轴对齐）
    ALIGNED = "aligned"              # 平面对齐（两平面法线反向）
    DISTANCE = "distance"            # 距离约束（两元素间距固定）
    FIXED = "fixed"                  # 固定到原点（自由度=0）


# ── 零件实例 ──────────────────────────

@dataclass
class AssemblyPart:
    """装配中的一个零件实例。"""
    instance_id: str                     # 如 "base_01", "bolt_01"
    part_type: PartType                  # 基础零件类型
    requirements: RequirementDocument    # 零件自身的尺寸/材料需求
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)  # (x, y, z) mm
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    material: str = ""
    color: tuple[int, int, int] = (180, 180, 200)  # RGB, 用于区分

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "part_type": self.part_type.value,
            "requirements": self.requirements.model_dump(mode="json"),
            "position": list(self.position),
            "rotation_deg": list(self.rotation_deg),
            "material": self.material,
            "color": list(self.color),
        }


# ── 零件间约束 ────────────────────────

@dataclass
class AssemblyConstraint:
    """零件间的几何约束。"""
    instance_from: str
    instance_to: str
    constraint_type: ConstraintType
    params: dict[str, Any] = field(default_factory=dict)  # face_id, axis_id 等

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_from": self.instance_from,
            "instance_to": self.instance_to,
            "constraint_type": self.constraint_type.value,
            "params": self.params,
        }


# ── 装配设计 ─────────────────────────

@dataclass
class AssemblyDesign:
    """完整的装配方案。"""
    assembly_name: str
    parts: list[AssemblyPart]
    constraints: list[AssemblyConstraint]
    description: str = ""
    total_mass_kg: float = 0.0  # 估算值（各零件体积×密度）
    bounding_box: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assembly_name": self.assembly_name,
            "description": self.description,
            "parts": [p.to_dict() for p in self.parts],
            "constraints": [c.to_dict() for c in self.constraints],
            "total_mass_kg": self.total_mass_kg,
            "bounding_box": list(self.bounding_box),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @property
    def part_count(self) -> int:
        return len(self.parts)

    @property
    def constraint_count(self) -> int:
        return len(self.constraints)


# ── Assembly Agent ─────────────────────

class AssemblyAgent:
    """装配 Agent：将用户对装配的描述 → AssemblyDesign。

    描述示例：
      "设计一个由底板 + 支架 + 电机轴组成的安装座"
      "一个包含两个M6螺栓的法兰"
    """

    def __init__(self, verbose: bool = False) -> None:
        self._log: AgentLogger = get_logger("assembly_agent", verbose=verbose)

    # ── 简化启发式：从关键词推断零件 ─

    def design_from_description(self, description: str,
                                  name: str = "assembly_01") -> AssemblyDesign:
        """从自然语言描述构造装配方案。"""
        with self._log.measure_stage("design", description=description[:60]):
            parts: list[AssemblyPart] = []
            constraints: list[AssemblyConstraint] = []
            lower = description.lower()

            counter = 1
            instance_counter: dict[str, int] = {}

            def _inst(tag: str) -> str:
                n = instance_counter.get(tag, 0) + 1
                instance_counter[tag] = n
                return f"{tag}_{n:02d}"

            if any(w in lower for w in ["底板", "base", "plate", "底座"]):
                parts.append(AssemblyPart(
                    instance_id=_inst("base"),
                    part_type=PartType.PLATE,
                    requirements=RequirementDocument(
                        part_type=PartType.PLATE,
                        dimensions={"length": 200.0, "width": 100.0,
                                    "height": 10.0},
                        material="Q235",
                        description="底板/底座",
                    ),
                    position=(0.0, 0.0, 0.0),
                    color=(140, 140, 160),
                ))

            if any(w in lower for w in ["支架", "bracket", "角座"]):
                parts.append(AssemblyPart(
                    instance_id=_inst("bracket"),
                    part_type=PartType.BRACKET,
                    requirements=RequirementDocument(
                        part_type=PartType.BRACKET,
                        dimensions={"length": 80.0, "width": 80.0,
                                    "height": 8.0},
                        material="Q235",
                        description="L形支架",
                    ),
                    position=(50.0, 50.0, 10.0),  # 放置在底板上方
                    color=(200, 160, 120),
                ))

            if any(w in lower for w in ["电机", "motor", "电机轴", "shaft"]):
                parts.append(AssemblyPart(
                    instance_id=_inst("shaft"),
                    part_type=PartType.SHAFT,
                    requirements=RequirementDocument(
                        part_type=PartType.SHAFT,
                        dimensions={"length": 250.0, "diameter": 20.0},
                        material="45 steel",
                        description="电机传动轴",
                    ),
                    position=(50.0, 50.0, 18.0),
                    color=(100, 150, 200),
                ))

            if any(w in lower for w in ["法兰", "flange"]):
                parts.append(AssemblyPart(
                    instance_id=_inst("flange"),
                    part_type=PartType.FLANGE,
                    requirements=RequirementDocument(
                        part_type=PartType.FLANGE,
                        dimensions={"diameter": 100.0, "thickness": 15.0,
                                    "hole_diameter": 10.0},
                        material="Q235",
                        description="法兰盘",
                    ),
                    position=(100.0, 50.0, 0.0),
                    color=(220, 180, 100),
                ))

            if any(w in lower for w in ["螺丝", "螺栓", "bolt", "螺丝"]):
                parts.append(AssemblyPart(
                    instance_id=_inst("bolt"),
                    part_type=PartType.SHAFT,
                    requirements=RequirementDocument(
                        part_type=PartType.SHAFT,
                        dimensions={"length": 16.0, "diameter": 6.0},
                        material="8.8 steel",
                        description="M6螺栓",
                    ),
                    position=(20.0, 50.0, 0.0),
                    color=(240, 240, 80),
                ))
                parts.append(AssemblyPart(
                    instance_id=_inst("bolt"),
                    part_type=PartType.SHAFT,
                    requirements=RequirementDocument(
                        part_type=PartType.SHAFT,
                        dimensions={"length": 16.0, "diameter": 6.0},
                        material="8.8 steel",
                        description="M6螺栓",
                    ),
                    position=(180.0, 50.0, 0.0),
                    color=(240, 240, 80),
                ))

            if any(w in lower for w in ["齿轮", "gear"]):
                parts.append(AssemblyPart(
                    instance_id=_inst("gear"),
                    part_type=PartType.GEAR,
                    requirements=RequirementDocument(
                        part_type=PartType.GEAR,
                        dimensions={"pitch_diameter": 80.0,
                                    "thickness": 15.0, "hole_diameter": 20.0,
                                    "module": 2.0, "teeth": 40.0},
                        material="20CrMnTi",
                        description="齿轮 M2 Z40",
                    ),
                    position=(50.0, 50.0, 50.0),
                    color=(200, 100, 100),
                ))

            # 如果完全匹配不到，创建一个默认盒体
            if not parts:
                parts.append(AssemblyPart(
                    instance_id=_inst("default"),
                    part_type=PartType.BOX,
                    requirements=RequirementDocument(
                        part_type=PartType.BOX,
                        dimensions={"length": 100.0, "width": 50.0,
                                    "height": 25.0},
                        material="steel",
                        description="默认零件",
                    ),
                    position=(0.0, 0.0, 0.0),
                ))

            # 生成约束 — 所有后续零件与第一个零件 FACE_CONTACT
            first = parts[0].instance_id
            for p in parts[1:]:
                constraints.append(AssemblyConstraint(
                    instance_from=first,
                    instance_to=p.instance_id,
                    constraint_type=ConstraintType.FACE_CONTACT,
                    params={"faces": "top→bottom", "clearance_mm": 0.02},
                ))

            # 估算总质量（简单：按体积×7.8e-6 kg/mm³）
            total_vol = 0.0
            max_x = max_y = max_z = 0.0
            for p in parts:
                dims = p.requirements.dimensions
                if "length" in dims and "width" in dims and "height" in dims:
                    v = dims["length"] * dims["width"] * dims["height"]
                elif "diameter" in dims and "length" in dims:
                    r = dims["diameter"] * 0.5
                    v = 3.14159 * r * r * dims["length"]
                else:
                    v = sum(dims.values()) * 1000.0
                total_vol += v
                max_x = max(max_x, p.position[0] + dims.get("length", 10))
                max_y = max(max_y, p.position[1] + dims.get("width", 10))
                max_z = max(max_z, p.position[2] + dims.get("height", 10))

            design = AssemblyDesign(
                assembly_name=name,
                description=description,
                parts=parts,
                constraints=constraints,
                total_mass_kg=round(total_vol * 7.8e-6, 4),
                bounding_box=(round(max_x, 2), round(max_y, 2),
                              round(max_z, 2)),
            )
            self._log.task("assembly", "designed",
                           parts=design.part_count,
                           constraints=design.constraint_count)
            return design

    def design_from_parts(
        self,
        part_specs: list[tuple[str, dict[str, float], str]],
        assembly_name: str = "custom_assembly",
    ) -> AssemblyDesign:
        """程序化构造：(part_type_tag, dims, material) 列表。"""
        parts: list[AssemblyPart] = []
        z_cursor = 0.0
        for idx, (pt, dims, mat) in enumerate(part_specs):
            try:
                ptype = PartType(pt) if pt in (e.value for e in PartType) else PartType.BOX
            except (ValueError, TypeError):
                ptype = PartType.BOX

            if not dims:
                if ptype == PartType.BOX:
                    dims = {"length": 100.0, "width": 50.0, "height": 25.0}
                elif ptype in (PartType.SHAFT, PartType.CYLINDER):
                    dims = {"length": 100.0, "diameter": 20.0}
                else:
                    dims = {"length": 100.0, "width": 50.0, "height": 25.0}

            tag = ptype.value
            inst = AssemblyPart(
                instance_id=f"{tag}_{idx + 1:02d}",
                part_type=ptype,
                requirements=RequirementDocument(
                    part_type=ptype,
                    dimensions=dims,
                    material=mat or "steel",
                ),
                position=(0.0, 0.0, z_cursor),
            )
            z_cursor += dims.get("height", dims.get("length", 50.0))
            parts.append(inst)

        constraints: list[AssemblyConstraint] = []
        for i in range(1, len(parts)):
            constraints.append(AssemblyConstraint(
                instance_from=parts[0].instance_id,
                instance_to=parts[i].instance_id,
                constraint_type=ConstraintType.FACE_CONTACT,
                params={"faces": "bottom→top"},
            ))

        return AssemblyDesign(
            assembly_name=assembly_name,
            parts=parts,
            constraints=constraints,
            description="程序化生成的装配方案",
        )


# ── Assembly Executor ──────────────────

class AssemblyExecutor:
    """将 AssemblyDesign 转换成：
      - 一份 FreeCAD Python 脚本（伪实现，给出脚本结构）
      - 一份 BOM（物料清单）
    """

    def __init__(self, verbose: bool = False) -> None:
        self._log: AgentLogger = get_logger("assembly_executor",
                                             verbose=verbose)

    def generate_script(self, design: AssemblyDesign) -> str:
        """生成 FreeCAD Python 装配脚本框架（伪代码，便于调试）。"""
        lines = [
            "# Auto-generated by fc.agent — Assembly Script",
            f"# Assembly: {design.assembly_name}",
            f"# Parts: {design.part_count}, Constraints: {design.constraint_count}",
            "import FreeCAD",
            "import Part",
            "from FreeCAD import Base",
            "",
            "doc = FreeCAD.newDocument()",
            "",
        ]
        for p in design.parts:
            x, y, z = p.position
            dims = p.requirements.dimensions
            if any(k in dims for k in ("length", "width", "height")):
                lines.append(
                    f"# {p.instance_id} — {p.part_type.value} "
                    f"{dims}"
                )
                lines.append(
                    f"box = doc.addObject('Part::Box', '{p.instance_id}')"
                )
                lines.append(
                    f"box.Length = {dims.get('length', 100)}"
                )
                lines.append(
                    f"box.Width = {dims.get('width', 50)}"
                )
                lines.append(
                    f"box.Height = {dims.get('height', 25)}"
                )
                lines.append(
                    f"box.Placement = FreeCAD.Placement("
                    f"FreeCAD.Vector({x}, {y}, {z}), "
                    f"FreeCAD.Rotation(0, 0, 0))"
                )
            else:
                lines.append(
                    f"# {p.instance_id} — cylinder "
                    f"(diameter={dims.get('diameter', 10)}, "
                    f"length={dims.get('length', 50)})"
                )
                lines.append(
                    f"cyl = doc.addObject('Part::Cylinder', "
                    f"'{p.instance_id}')"
                )
                lines.append(
                    f"cyl.Radius = {dims.get('diameter', 10) / 2}"
                )
                lines.append(
                    f"cyl.Height = {dims.get('length', 50)}"
                )
            lines.append("")

        lines += [
            "# Constraints (示意：后续可通过 Assembly workbench 添加)",
        ]
        for c in design.constraints:
            lines.append(
                f"# [{c.constraint_type.value}] "
                f"{c.instance_from} -> {c.instance_to} : {c.params}"
            )
        lines += [
            "",
            "doc.recompute()",
            "",
            "# Bounding box estimate:",
            f"#   {design.bounding_box}",
            f"# Total mass ~ {design.total_mass_kg:.4f} kg",
        ]
        return "\n".join(lines)

    def generate_bom(self, design: AssemblyDesign) -> dict[str, Any]:
        """生成 BOM（物料清单）字典。"""
        bom_lines: list[dict[str, Any]] = []
        for p in design.parts:
            bom_lines.append({
                "instance": p.instance_id,
                "part_type": p.part_type.value,
                "material": p.material or p.requirements.material,
                "dimensions": p.requirements.dimensions,
                "position": list(p.position),
            })

        return {
            "assembly_name": design.assembly_name,
            "part_count": design.part_count,
            "constraint_count": design.constraint_count,
            "total_mass_kg": design.total_mass_kg,
            "bounding_box_mm": list(design.bounding_box),
            "items": bom_lines,
        }
