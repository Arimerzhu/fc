"""需求分析Agent基础版 — 自然语言→结构化需求JSON。

方法论v1.0 P0-2：消除需求歧义，避免设计阶段返工。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .agent_schemas import (
    Connector,
    ConstraintType,
    PartType,
    RequirementDocument,
    Standard,
    ToleranceGrade,
)

# ── 关键词识别词典 ──────────────────────────────────────────────

_PART_TYPE_KEYWORDS: dict[PartType, list[str]] = {
    PartType.BOX: ["box", "方块", "立方体", "长方体"],
    PartType.CYLINDER: ["cylinder", "圆柱", "圆柱体"],
    PartType.SPHERE: ["sphere", "球", "球体"],
    PartType.CONE: ["cone", "圆锥", "圆锥体"],
    PartType.TORUS: ["torus", "环", "圆环"],
    PartType.SHAFT: ["shaft", "轴", "传动轴", "转轴"],
    PartType.GEAR: ["gear", "齿轮"],
    PartType.HOUSING: ["housing", "箱体", "壳体"],
    PartType.BRACKET: ["bracket", "支架", "支撑架", "安装支架"],
    PartType.FLANGE: ["flange", "法兰"],
    PartType.PLATE: ["plate", "平板", "底板"],
}

_MATERIAL_KEYWORDS: dict[str, list[str]] = {
    "Q235": ["q235", "普通碳钢"],
    "45#": ["45#", "45号钢", "45钢"],
    "40Cr": ["40cr", "40铬"],
    "20CrMnTi": ["20crmnti"],
    "HT200": ["ht200", "灰铸铁"],
    "HT250": ["ht250"],
    "ZL104": ["zl104", "铝合金"],
    "6061": ["6061", "铝"],
    "ABS": ["abs", "塑料"],
}

_TOLERANCE_KEYWORDS: dict[ToleranceGrade, list[str]] = {
    ToleranceGrade.IT5: ["高精度", "精密", "it5"],
    ToleranceGrade.IT6: ["较精密", "高精密", "it6"],
    ToleranceGrade.IT7: ["一般", "普通", "中等精度", "it7"],
    ToleranceGrade.IT8: ["一般精度", "it8"],
    ToleranceGrade.IT9: ["粗糙", "低精度", "it9"],
    ToleranceGrade.IT10: ["很低精度", "it10"],
}

_STANDARD_KEYWORDS: dict[Standard, list[str]] = {
    Standard.GB: ["gb", "国标", "中国标准", "国家标准"],
    Standard.ISO: ["iso", "国际标准"],
    Standard.ANSI: ["ansi", "美标", "美国标准"],
}


@dataclass
class ParseResult:
    """需求分析Agent的解析中间结果。"""
    part_type: PartType
    dimensions: dict[str, float]
    material: str
    tolerance: ToleranceGrade
    standard: Standard
    description: str
    connectors: list[Connector]


class RequirementAgent:
    """需求分析Agent。

    将自然语言设计需求解析为结构化 RequirementDocument。
    实现：规则+正则的确定性解析（基础版），可替换为LLM推理。
    """

    def parse(self, user_input: str) -> RequirementDocument:
        """解析自然语言需求。"""
        text = user_input.strip()

        result = ParseResult(
            part_type=self._detect_part_type(text),
            dimensions=self._extract_dimensions(text),
            material=self._detect_material(text),
            tolerance=self._detect_tolerance(text),
            standard=self._detect_standard(text),
            description=text,
            connectors=self._extract_connectors(text),
        )

        # 若未识别到任何尺寸，按零件类型给默认值保证能继续
        if not result.dimensions:
            result.dimensions = self._default_dimensions(result.part_type)

        return RequirementDocument(
            part_type=result.part_type,
            dimensions=result.dimensions,
            material=result.material,
            tolerance_grade=result.tolerance,
            standard=result.standard,
            quantity=self._extract_quantity(text),
            description=result.description,
            connectors=result.connectors,
        )

    def parse_json(self, user_input: str) -> str:
        """返回JSON字符串，用于Agent间传递。"""
        return self.parse(user_input).model_dump_json(indent=2)

    # ── 内部识别方法 ─────────────────────────────────────────────

    def _detect_part_type(self, text: str) -> PartType:
        lower = text.lower()
        for ptype, keywords in _PART_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in lower:
                    return ptype
        return PartType.CUSTOM

    def _extract_dimensions(self, text: str) -> dict[str, float]:
        dims: dict[str, float] = {}

        # 模式 2 (优先): "10x20x30" / "100x50" — 避免 x 被其他规则误解析
        m3d = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)", text)
        if m3d:
            dims.update({"length": float(m3d.group(1)),
                         "width": float(m3d.group(2)),
                         "height": float(m3d.group(3))})
            return dims

        m2d = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)", text)
        if m2d:
            dims.update({"length": float(m2d.group(1)),
                         "width": float(m2d.group(2))})
            return dims

        # 模式 1: "长10 宽20 高30" / "length=10"
        # 单字母 d/r 使用单词边界，避免误匹配设计/其他单词
        for key, pattern in [
            ("length", r"(?:长|长度|length)\b[^0-9-]*(-?\d+(?:\.\d+)?)"),
            ("width", r"(?:宽|宽度|width)\b[^0-9-]*(-?\d+(?:\.\d+)?)"),
            ("height", r"(?:高|高度|height|thickness)\b[^0-9-]*(-?\d+(?:\.\d+)?)"),
            ("diameter", r"(?:直径|外径|diameter|dia|\bd\b)[^0-9-]*(-?\d+(?:\.\d+)?)"),
            ("inner_diameter", r"(?:内径|id)\b[^0-9-]*(-?\d+(?:\.\d+)?)"),
            ("radius", r"(?:半径|radius|\br\b)[^0-9-]*(-?\d+(?:\.\d+)?)"),
            ("hole_diameter", r"(?:孔直径|孔径)[^0-9-]*(-?\d+(?:\.\d+)?)"),
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                val = float(m.group(1))
                if val > 0:
                    dims[key] = val

        # 模式 3: "D=50" / "--param Length=100"
        for m in re.finditer(r"(?:--param\s+)?(\w+)\s*[=:]\s*(-?\d+(?:\.\d+)?)", text):
            key = m.group(1).lower()
            val = float(m.group(2))
            if val <= 0:
                continue
            if key in ("length", "l", "长"):
                dims.setdefault("length", val)
            elif key in ("width", "w", "宽"):
                dims.setdefault("width", val)
            elif key in ("height", "h", "thickness", "高"):
                dims.setdefault("height", val)
            elif key in ("diameter", "d", "dia", "直径"):
                dims.setdefault("diameter", val)
            elif key in ("radius", "r", "半径"):
                dims.setdefault("radius", val)

        return dims

    def _detect_material(self, text: str) -> str:
        lower = text.lower()
        for material, keywords in _MATERIAL_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    return material
        return "Q235"

    def _detect_tolerance(self, text: str) -> ToleranceGrade:
        lower = text.lower()
        for tol, keywords in _TOLERANCE_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    return tol
        return ToleranceGrade.IT7

    def _detect_standard(self, text: str) -> Standard:
        lower = text.lower()
        for std, keywords in _STANDARD_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    return std
        return Standard.GB

    def _extract_quantity(self, text: str) -> int:
        m = re.search(r"数量[^\d]*(\d+)|(\d+)\s*个|(\d+)\s*件", text)
        if m:
            val = int(m.group(1) or m.group(2) or m.group(3) or "1")
            return max(1, val)
        return 1

    def _extract_connectors(self, text: str) -> list[Connector]:
        """从文本中识别连接点（如"左端连接"、"螺栓孔在0,0,0"）。"""
        connectors: list[Connector] = []
        # 简单模式: "connector <name> at <x>,<y>,<z> with <constraint>"
        for m in re.finditer(
            r"connector\s+(\w+)\s+at\s+([\d.,\-]+)\s+with\s+(\w+)",
            text, re.IGNORECASE,
        ):
            try:
                connectors.append(Connector(
                    name=m.group(1),
                    position=m.group(2).replace(" ", ""),
                    constraint_type=ConstraintType(m.group(3).lower()),
                ))
            except (ValueError, AssertionError):
                continue
        return connectors

    def _default_dimensions(self, part_type: PartType) -> dict[str, float]:
        """零件类型默认尺寸（仅在完全无法识别时使用）。"""
        defaults = {
            PartType.BOX: {"length": 100.0, "width": 50.0, "height": 25.0},
            PartType.CYLINDER: {"radius": 25.0, "height": 100.0},
            PartType.SPHERE: {"radius": 50.0},
            PartType.CONE: {"radius1": 30.0, "radius2": 15.0, "height": 50.0},
            PartType.TORUS: {"radius1": 50.0, "radius2": 10.0},
            PartType.PLATE: {"length": 150.0, "width": 100.0, "thickness": 10.0},
            PartType.SHAFT: {"length": 100.0, "diameter": 20.0},
            PartType.GEAR: {"diameter": 100.0, "thickness": 20.0, "hole_diameter": 20.0},
            PartType.HOUSING: {"length": 200.0, "width": 120.0, "height": 80.0},
            PartType.BRACKET: {"length": 100.0, "width": 60.0, "thickness": 10.0},
            PartType.FLANGE: {"diameter": 100.0, "thickness": 15.0, "hole_diameter": 20.0},
            PartType.CUSTOM: {"length": 50.0, "width": 50.0, "height": 50.0},
        }
        return defaults.get(part_type, defaults[PartType.CUSTOM])

    # ── 调试辅助 ───────────────────────────────────────────────

    def to_dict(self, doc: RequirementDocument) -> dict:
        return json.loads(doc.model_dump_json())
