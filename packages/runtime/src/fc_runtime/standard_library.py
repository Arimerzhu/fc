"""零件标准库预设 — P2.3

提供常用标准件的尺寸预设（ISO/GB/ANSI），以及自定义零件模板。
调用方式：StandardLibrary.get("bolt_m5_hex") → 直接拿到 RequirementDocument。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fc_runtime.agent_schemas import PartType, RequirementDocument, Standard, ToleranceGrade


@dataclass
class StandardPartDefinition:
    """标准件定义。"""
    code: str                    # 标准编号，如 "ISO 4017 M5x12"
    short_name: str              # 短名，如 "bolt_m5"
    part_type: PartType
    dimensions: dict[str, float]
    material: str = "Q235"
    tolerance: ToleranceGrade = ToleranceGrade.IT7
    standard: Standard = Standard.ISO
    description: str = ""

    def to_requirement(self) -> RequirementDocument:
        return RequirementDocument(
            part_type=self.part_type,
            dimensions=self.dimensions,
            material=self.material,
            tolerance_grade=self.tolerance,
            standard=self.standard,
            description=self.description,
        )


# ── 预设标准件库 ─────────────────────────────────

PRESET_PARTS: list[StandardPartDefinition] = [
    # 螺栓（ISO 4017 六角头螺栓）
    StandardPartDefinition(
        code="ISO 4017 M5x12",
        short_name="bolt_m5_12",
        part_type=PartType.SHAFT,
        dimensions={"length": 12.0, "diameter": 5.0},
        material="8.8 steel",
        standard=Standard.ISO,
        description="ISO 4017 六角头螺栓 M5×12",
    ),
    StandardPartDefinition(
        code="ISO 4017 M6x16",
        short_name="bolt_m6_16",
        part_type=PartType.SHAFT,
        dimensions={"length": 16.0, "diameter": 6.0},
        material="8.8 steel",
        standard=Standard.ISO,
        description="ISO 4017 六角头螺栓 M6×16",
    ),
    StandardPartDefinition(
        code="ISO 4017 M8x20",
        short_name="bolt_m8_20",
        part_type=PartType.SHAFT,
        dimensions={"length": 20.0, "diameter": 8.0},
        material="8.8 steel",
        standard=Standard.ISO,
        description="ISO 4017 六角头螺栓 M8×20",
    ),

    # 垫片
    StandardPartDefinition(
        code="ISO 7089 M5",
        short_name="washer_m5",
        part_type=PartType.PLATE,
        dimensions={"inner_diameter": 5.3, "diameter": 10.0, "thickness": 1.0},
        material="steel",
        standard=Standard.ISO,
        description="ISO 7089 平垫片 M5",
    ),
    StandardPartDefinition(
        code="ISO 7089 M10",
        short_name="washer_m10",
        part_type=PartType.PLATE,
        dimensions={"inner_diameter": 10.5, "diameter": 20.0, "thickness": 2.0},
        material="steel",
        standard=Standard.ISO,
        description="ISO 7089 平垫片 M10",
    ),

    # 螺母
    StandardPartDefinition(
        code="ISO 4032 M6",
        short_name="nut_m6",
        part_type=PartType.HOUSING,
        dimensions={"outer_diameter": 10.0, "height": 5.2, "inner_diameter": 6.0},
        material="8.8 steel",
        standard=Standard.ISO,
        description="ISO 4032 六角螺母 M6",
    ),

    # 轴承（深沟球 62xx 系列，简化）
    StandardPartDefinition(
        code="ISO 15 6201",
        short_name="bearing_6201",
        part_type=PartType.CYLINDER,
        dimensions={"inner_diameter": 12.0, "outer_diameter": 32.0, "thickness": 10.0},
        material="Chrome steel 100Cr6",
        standard=Standard.ISO,
        tolerance=ToleranceGrade.IT5,
        description="深沟球轴承 6201，内径12×外径32×厚10mm",
    ),
    StandardPartDefinition(
        code="ISO 15 6203",
        short_name="bearing_6203",
        part_type=PartType.CYLINDER,
        dimensions={"inner_diameter": 17.0, "outer_diameter": 40.0, "thickness": 12.0},
        material="Chrome steel 100Cr6",
        standard=Standard.ISO,
        tolerance=ToleranceGrade.IT5,
        description="深沟球轴承 6203，内径17×外径40×厚12mm",
    ),

    # 法兰（EN 1092-1 PN10 简化）
    StandardPartDefinition(
        code="EN 1092-1 PN10 DN20",
        short_name="flange_dn20_pn10",
        part_type=PartType.FLANGE,
        dimensions={"diameter": 105.0, "thickness": 14.0, "hole_diameter": 14.0},
        material="Carbon steel",
        standard=Standard.ISO,
        description="PN10 法兰 DN20（3/4\"）",
    ),

    # 齿轮（简化模型）
    StandardPartDefinition(
        code="ANSI B29.1 M1 Z20",
        short_name="gear_m1_z20",
        part_type=PartType.GEAR,
        dimensions={"pitch_diameter": 20.0, "thickness": 10.0,
                    "hole_diameter": 6.0, "module": 1.0, "teeth": 20.0},
        material="18CrNiMo7-6",
        standard=Standard.ANSI,
        tolerance=ToleranceGrade.IT6,
        description="渐开线圆柱齿轮 M1 Z20",
    ),

    # 轴（多种长度组合）
    StandardPartDefinition(
        code="DIN 668 A 20x100",
        short_name="shaft_20x100",
        part_type=PartType.SHAFT,
        dimensions={"length": 100.0, "diameter": 20.0},
        material="C45 steel",
        standard=Standard.ISO,
        description="传动轴 Φ20×100mm",
    ),

    # 型材（铝制 T 槽）
    StandardPartDefinition(
        code="GB/T 6892 2020 Aluminium profile 40x40",
        short_name="alu_profile_40x40x200",
        part_type=PartType.BOX,
        dimensions={"length": 200.0, "width": 40.0, "height": 40.0},
        material="6063-T5 Aluminum",
        standard=Standard.GB,
        description="工业铝型材 40×40，长度200mm",
    ),

    # 支架
    StandardPartDefinition(
        code="Custom L-bracket 80x80",
        short_name="l_bracket_80",
        part_type=PartType.BRACKET,
        dimensions={"length": 80.0, "width": 80.0, "thickness": 5.0},
        material="Q235",
        standard=Standard.GB,
        description="L形直角支架 80×80×5mm",
    ),
]


class StandardLibrary:
    """标准件库 — 检索与构造。"""

    def __init__(self) -> None:
        self._by_short = {p.short_name: p for p in PRESET_PARTS}
        self._by_code = {p.code: p for p in PRESET_PARTS}

    def list_all(self) -> list[str]:
        """列出所有可用标准件的 short_name。"""
        return list(self._by_short.keys())

    def get(self, short_name: str) -> StandardPartDefinition | None:
        return self._by_short.get(short_name)

    def get_requirement(self, short_name: str) -> RequirementDocument | None:
        part = self._by_short.get(short_name)
        return part.to_requirement() if part else None

    def search(self, keyword: str) -> list[StandardPartDefinition]:
        k = keyword.lower()
        return [p for p in PRESET_PARTS
                if k in p.short_name.lower() or k in p.code.lower()
                or k in p.description.lower()]

    def search_by_part_type(self, part_type: PartType) -> list[StandardPartDefinition]:
        return [p for p in PRESET_PARTS if p.part_type == part_type]

    # ── 便利方法：快速创建常用零件 ─────────

    def bolt(self, m_size: str, length: float) -> StandardPartDefinition:
        """按 m_size 创建自定义螺栓（如 m="m6", length=20.0）。"""
        diameter = float(m_size.lower().replace("m", ""))
        return StandardPartDefinition(
            code=f"Custom M{int(diameter)}x{length}",
            short_name=f"custom_bolt_m{int(diameter)}_{length}",
            part_type=PartType.SHAFT,
            dimensions={"length": length, "diameter": diameter},
            material="8.8 steel",
            standard=Standard.ISO,
            description=f"自定义六角头螺栓 M{int(diameter)}x{length}",
        )

    def gear_by_module(self, module: float, teeth: int,
                        thickness: float = 15.0,
                        hole_diameter: float | None = None) -> StandardPartDefinition:
        """按模数/齿数创建齿轮。"""
        pitch = module * teeth
        hole = hole_diameter or pitch * 0.2
        return StandardPartDefinition(
            code=f"Custom gear M{module} Z{teeth}",
            short_name=f"custom_gear_m{module}_z{teeth}",
            part_type=PartType.GEAR,
            dimensions={"pitch_diameter": pitch, "thickness": thickness,
                        "hole_diameter": hole, "module": module, "teeth": float(teeth)},
            material="18CrNiMo7-6",
            standard=Standard.ISO,
            tolerance=ToleranceGrade.IT6,
            description=f"自定义齿轮 M{module} Z{teeth}",
        )


# ── 默认实例 ──────────────────────────────────

_default_library: StandardLibrary | None = None


def get_library() -> StandardLibrary:
    """获取默认标准件库实例。"""
    global _default_library
    if _default_library is None:
        _default_library = StandardLibrary()
    return _default_library
