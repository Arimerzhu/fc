"""装配 BOM（物料清单）模块 - 从 STEP 文件提取零件信息。

符合 GB/T 10609.2 明细表规范。

功能:
  1. 解析 STEP 文件中的 PRODUCT / PRODUCT_DEFINITION / NAUO 结构
  2. 提取零件名称、ID、数量
  3. 生成标准明细表数据
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any



def decode_step_string(s: str) -> str:
    """解码 ISO 10303-21 STEP 字符串编码 (\X2\hex\X0\ -> Unicode)。"""
    def _decode_x2(match: re.Match) -> str:
        hex_str = match.group(1)
        result = ""
        for i in range(0, len(hex_str), 4):
            if i + 4 <= len(hex_str):
                code = int(hex_str[i : i + 4], 16)
                result += chr(code)
        return result

    return re.sub(r"\\X2\\([0-9A-Fa-f]+)\\X0\\", _decode_x2, s)


class MaterialCategory(str, Enum):
    """常用工程材料类别。"""
    STEEL = "钢"
    CAST_IRON = "铸铁"
    ALUMINUM = "铝合金"
    COPPER = "铜合金"
    PLASTIC = "塑料"
    RUBBER = "橡胶"
    STANDARD = "标准件"
    OTHER = "其他"


@dataclass
class BOMItem:
    """明细表中的一行 - 一个零件/组件。"""
    item_no: int
    name: str
    name_en: str = ""
    quantity: int = 1
    material: str = ""
    mass_kg: float = 0.0
    drawing_no: str = ""
    remark: str = ""
    step_id: str = ""
    is_assembly: bool = False
    children: list[int] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        if self.name_en:
            return f"{self.name} ({self.name_en})"
        return self.name


@dataclass
class BOMTable:
    """完整的物料清单。"""
    title: str = ""
    drawing_no: str = ""
    items: list[BOMItem] = field(default_factory=list)
    assembly_name: str = ""

    @property
    def total_parts(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def total_mass_kg(self) -> float:
        return sum(item.mass_kg * item.quantity for item in self.items)

    def add_item(self, **kwargs: Any) -> BOMItem:
        item_no = len(self.items) + 1
        item = BOMItem(item_no=item_no, **kwargs)
        self.items.append(item)
        return item

    def get_item(self, item_no: int) -> BOMItem | None:
        for item in self.items:
            if item.item_no == item_no:
                return item
        return None

    def sort_by_item_no(self) -> None:
        self.items.sort(key=lambda x: x.item_no)


# ── STEP 解析 ────────────────────────────────────────────────────


def _parse_step_entities(filepath: str) -> dict[int, str]:
    """解析 STEP 文件，返回 {id: content} 映射。"""
    entities: dict[int, str] = {}
    in_data = False
    with open(filepath, "r", encoding="latin-1") as f:
        for line in f:
            stripped = line.strip()
            if stripped == "DATA;":
                in_data = True
                continue
            if stripped == "ENDSEC;" and in_data:
                break
            if not in_data:
                continue
            m = re.match(r"#(\d+)\s*=\s*(.+)", stripped)
            if m:
                eid = int(m.group(1))
                entities[eid] = m.group(2)
    return entities


def _extract_product_names(entities: dict[int, str]) -> dict[int, str]:
    """从 PRODUCT 实体提取零件名称。"""
    names: dict[int, str] = {}
    pattern = re.compile(r"PRODUCT\s*\(\s*'([^']*)'")
    for eid, content in entities.items():
        if "PRODUCT_DEFINITION" in content or "PRODUCT_RELATED" in content:
            continue
        m = pattern.match(content)
        if m:
            names[eid] = m.group(1)
    return names


def _extract_nauo(entities: dict[int, str]) -> list[tuple[int, int, int]]:
    """从 NEXT_ASSEMBLY_USAGE_OCCURRENCE 提取装配关系。"""
    relations: list[tuple[int, int, int]] = []
    pattern = re.compile(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\([^)]*#(\d+)[^#]*#(\d+)")
    for eid, content in entities.items():
        m = pattern.match(content)
        if m:
            asm_ref = int(m.group(1))
            part_ref = int(m.group(2))
            relations.append((asm_ref, part_ref, eid))
    return relations


def _resolve_entity_name(
    eid: int, entities: dict[int, str], product_names: dict[int, str]
) -> str:
    """通过引用链解析实体名称。"""
    if eid in product_names:
        return decode_step_string(product_names[eid])
    content = entities.get(eid, "")
    refs = re.findall(r"#(\d+)", content)
    for ref_str in refs:
        ref = int(ref_str)
        if ref in product_names:
            return decode_step_string(product_names[ref])
        ref_content = entities.get(ref, "")
        refs2 = re.findall(r"#(\d+)", ref_content)
        for ref2_str in refs2:
            ref2 = int(ref2_str)
            if ref2 in product_names:
                return decode_step_string(product_names[ref2])
    return f"Part_{eid}"


def parse_step_bom(filepath: str) -> BOMTable:
    """从 STEP 文件解析装配 BOM。"""
    entities = _parse_step_entities(filepath)
    product_names = _extract_product_names(entities)
    nauo = _extract_nauo(entities)

    bom = BOMTable()
    if not nauo:
        return bom

    part_counts: dict[int, int] = {}
    assembly_ids: set[int] = set()
    for asm_ref, part_ref, _ in nauo:
        assembly_ids.add(asm_ref)
        part_counts[part_ref] = part_counts.get(part_ref, 0) + 1

    if assembly_ids:
        asm_id = next(iter(assembly_ids))
        bom.assembly_name = decode_step_string(_resolve_entity_name(asm_id, entities, product_names))

    for part_ref, count in sorted(part_counts.items(), key=lambda x: x[0]):
        name = _resolve_entity_name(part_ref, entities, product_names)
        bom.add_item(name=name, quantity=count, step_id=str(part_ref))

    return bom


# ── 手动构建辅助 ────────────────────────────────────────────────


def make_bom_from_list(parts: list[dict[str, Any]]) -> BOMTable:
    """从字典列表快速构建 BOM。"""
    bom = BOMTable()
    for p in parts:
        bom.add_item(**p)
    return bom


def make_sample_bom() -> BOMTable:
    """生成示例 BOM（进纸机构）。"""
    bom = BOMTable(title="进纸机构装配图", assembly_name="进纸机构")
    sample_parts = [
        {"name": "机架", "name_en": "Frame", "quantity": 1, "material": "Q235"},
        {"name": "后踏板", "name_en": "Pedal Lift", "quantity": 1, "material": "Q235"},
        {"name": "减速器", "name_en": "Reducer", "quantity": 1, "material": "铸铁", "is_assembly": True},
        {"name": "升降台", "name_en": "Lift Platform", "quantity": 1, "material": "Q235"},
        {"name": "滑动组", "name_en": "Slide Assembly", "quantity": 2, "material": "GCr15", "is_assembly": True},
        {"name": "齿条组", "name_en": "Rack Assembly", "quantity": 2, "material": "45钢"},
        {"name": "凸轮轴", "name_en": "Camshaft", "quantity": 1, "material": "40Cr"},
        {"name": "摆杆轴", "name_en": "Pendulum Shaft", "quantity": 1, "material": "45钢"},
        {"name": "电机", "name_en": "Motor", "quantity": 1, "material": "标准件", "remark": "Y系列"},
        {"name": "螺栓 M10x30", "name_en": "Bolt M10x30", "quantity": 16, "material": "标准件"},
        {"name": "螺栓 M8x25", "name_en": "Bolt M8x25", "quantity": 8, "material": "标准件"},
        {"name": "轴承 6205", "name_en": "Bearing 6205", "quantity": 4, "material": "标准件"},
    ]
    for p in sample_parts:
        bom.add_item(**p)
    return bom
