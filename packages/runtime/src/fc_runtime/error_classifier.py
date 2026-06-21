"""三级错误分类器 — DESIGN/CODE/DRAWING错误精准回滚。

方法论v1.0 P0-3：基于ArtiCAD的错误分类策略。
验证失败时，仅回滚到责任Agent，而非整体重试。
"""

from __future__ import annotations

import re

from .agent_schemas import ErrorLevel


# ── DESIGN级错误：设计规划不合理，需回滚到设计规划Agent ─────

_DESIGN_PATTERNS: list[tuple[str, str]] = [
    # 几何退化（非流形、自相交通常源于设计参数不合理）
    (r"non.?manifold|non.?manifold|self.intersect|self.?intersect",
     "几何体非流形/自相交 — 设计参数冲突"),
    (r"degenerate|degenerated|zero.?volume|invalid.?shape|topology.*fail",
     "几何退化 — 关键尺寸不合理"),
    # 装配失败
    (r"assembly.*fail|constraint.*(?:fail|error)|mating.*fail|connector.*invalid",
     "装配约束失败 — Connector定义冲突"),
    # 参数冲突（设计层面的数量级错误）
    (r"thickness.*greater.*than|depth.*exceed|notch.*too.*(?:deep|large)|hole.*too.*(?:large|small)",
     "特征参数数量级冲突 — 需重新规划"),
    # 几何体为空
    (r"solid.*count.*<.*(?:expected|require)|实体.*<.*期望|几何.*为空",
     "几何构建产生空实体 — 设计参数无可行解"),
]

# ── CODE级错误：脚本执行/参数问题，需回滚到CAD建模Agent ─────

_CODE_PATTERNS: list[tuple[str, str]] = [
    # Python脚本执行错误
    (r"traceback|syntaxerror|nameerror|typeerror|valueerror|attributeerror|keyerror|indexerror",
     "Python脚本执行异常"),
    # 参数错误
    (r"invalid.*(?:parameter|value|argument)|out.*of.*range|must.*be.*(?:positive|greater|less)|非法.*参数",
     "参数数值非法或超出范围"),
    # FreeCAD对象/文档问题
    (r"no.*document|no.*active.*document|document.*not.*found|object.*not.*found|找不到.*对象|文档.*不存在",
     "FreeCAD文档/对象引用错误"),
    # 布尔运算失败
    (r"boolean.*(?:fail|error)|fusion.*fail|cut.*fail|common.*fail|common.*error",
     "布尔运算失败 — 几何不相干"),
    # 文件
    (r"file.*exists|already.*exist|文件.*已存在",
     "文件覆盖冲突"),
    # 超时
    (r"timeout|timed.?out|超时",
     "执行超时"),
    # FreeCAD内部错误
    (r"freecad.*(?:exception|error|fail)|fcstd.*(?:fail|error|invalid)|occ.*exception|opencascade",
     "FreeCAD/OpenCascade内部错误"),
]

# ── DRAWING级错误：出图相关，需回滚到出图Agent ─────

_DRAWING_PATTERNS: list[tuple[str, str]] = [
    (r"techdraw|draw(?:ing|page|view).*(?:fail|error|invalid)|视图.*(?:失败|错误)",
     "TechDraw视图/页面生成失败"),
    (r"dimension.*(?:fail|error|missing)|标注.*(?:失败|错误|缺失)|标注.*遗漏",
     "尺寸标注问题"),
    (r"gd&?t|tolerance.*(?:fail|error)|公差.*(?:错误|缺失)",
     "GD&T/公差标注问题"),
    (r"export.*(?:svg|dxf|pdf).*(?:fail|error)|(?:svg|dxf|pdf).*(?:fail|error)|导出.*(?:失败|错误)",
     "图纸导出失败"),
    (r"template.*(?:fail|error|missing|not.?found)|模板.*(?:失败|错误|缺失)",
     "图纸模板问题"),
    (r"projection.*(?:fail|error)|投影.*(?:失败|错误)",
     "投影方向问题"),
]


class ErrorClassifier:
    """三级错误分类器。

    将失败信息分类为 DESIGN / CODE / DRAWING，
    供编排器精准回滚到对应责任Agent。
    """

    def __init__(self) -> None:
        self._patterns = {
            ErrorLevel.DESIGN: _DESIGN_PATTERNS,
            ErrorLevel.CODE: _CODE_PATTERNS,
            ErrorLevel.DRAWING: _DRAWING_PATTERNS,
        }

    def classify(
        self,
        error_text: str,
        stderr_text: str = "",
        agent_stage: str | None = None,
    ) -> tuple[ErrorLevel, str]:
        """分类错误。

        Args:
            error_text: 主要错误信息
            stderr_text: stderr补充信息
            agent_stage: 可选，当前执行阶段("planning"|"modeling"|"drawing")
                        若未匹配到任何模式，则用此信息兜底。

        Returns:
            (错误等级, 错误说明)
        """
        combined = f"{error_text} {stderr_text}".lower()

        # 优先级：DESIGN > CODE > DRAWING
        for level in (ErrorLevel.DESIGN, ErrorLevel.CODE, ErrorLevel.DRAWING):
            for pattern, description in self._patterns[level]:
                if re.search(pattern, combined, re.IGNORECASE):
                    return level, description

        # 兜底：根据执行阶段判断
        if agent_stage == "drawing":
            return ErrorLevel.DRAWING, "出图阶段未知错误（默认DRAWING级）"
        if agent_stage == "planning":
            return ErrorLevel.DESIGN, "设计阶段未知错误（默认DESIGN级）"
        # 默认CODE级（建模阶段最常见的错误源）
        return ErrorLevel.CODE, "未知执行错误（默认CODE级）"

    # ── 便捷方法：直接从不同来源分类 ─────

    def from_exception(self, exc: Exception, agent_stage: str | None = None) -> tuple[ErrorLevel, str]:
        return self.classify(str(exc), repr(exc), agent_stage)

    def from_task_result(self, error: str, stderr: str,
                          agent_stage: str | None = None) -> tuple[ErrorLevel, str]:
        return self.classify(error, stderr, agent_stage)

    # ── 路由映射 ────────────────────────────────────────────

    def route_to(self, level: ErrorLevel) -> str:
        """返回应回滚到的Agent名称。"""
        return {
            ErrorLevel.DESIGN: "PlanningAgent",
            ErrorLevel.CODE: "CADModelingAgent",
            ErrorLevel.DRAWING: "DrawingAgent",
            ErrorLevel.NONE: "None",
        }[level]

    # ── 规则导出（供自动化测试与文档生成） ─────────────────────

    def export_rules(self) -> dict[str, list[dict[str, str]]]:
        return {
            level.value: [{"pattern": p, "description": d}
                           for p, d in patterns]
            for level, patterns in self._patterns.items()
        }
