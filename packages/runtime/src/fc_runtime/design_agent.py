"""设计规划Agent — RequirementDocument → ModelingPlan。

规则引擎：按 PartType 映射到可执行的特征步骤序列。
符合方法论v1.0第三章3.1节：参数化特征树，先粗后精的建模策略。
"""

from __future__ import annotations

from fc_runtime.agent_schemas import (
    Connector,
    FeatureOperation,
    FeatureStep,
    ModelingPlan,
    PartType,
    RequirementDocument,
)


def _box_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """BOX: length×width×height → PartPrimitive 直接 add box。"""
    length = dims.get("length", dims.get("L", 50.0))
    width = dims.get("width", dims.get("W", 30.0))
    height = dims.get("height", dims.get("H", 20.0))
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "rectangle", "length": length, "width": width},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.PAD,
            parameters={"distance": height},
            depends_on=[1],
        ),
    ]


def _cylinder_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """CYLINDER: radius + height → sketch circle + pad。"""
    radius = dims.get("radius", dims.get("R", 10.0))
    height = dims.get("height", dims.get("length", dims.get("H", 50.0)))
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "circle", "radius": radius},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.PAD,
            parameters={"distance": height},
            depends_on=[1],
        ),
    ]


def _sphere_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """SPHERE: radius → sketch semicircle + revolution。"""
    radius = dims.get("radius", dims.get("R", 20.0))
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "semicircle", "radius": radius},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.REVOLUTION,
            parameters={"angle": 360.0},
            depends_on=[1],
        ),
    ]


def _cone_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """CONE: radius1 + radius2 + height → sketch trapezoid + revolution。"""
    r1 = dims.get("radius1", dims.get("R1", 20.0))
    r2 = dims.get("radius2", dims.get("R2", 10.0))
    height = dims.get("height", dims.get("H", 40.0))
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "trapezoid", "radius1": r1, "radius2": r2, "height": height},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.REVOLUTION,
            parameters={"angle": 360.0},
            depends_on=[1],
        ),
    ]


def _torus_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """TORUS: radius1(主轴) + radius2(截面) → sketch circle + revolution。"""
    r1 = dims.get("radius1", dims.get("R1", 30.0))
    r2 = dims.get("radius2", dims.get("R2", 5.0))
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "circle", "radius": r2, "offset_x": r1},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.REVOLUTION,
            parameters={"angle": 360.0},
            depends_on=[1],
        ),
    ]


def _plate_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """PLATE: length×width×thickness → 矩形 + 薄拉伸。"""
    length = dims.get("length", dims.get("L", 100.0))
    width = dims.get("width", dims.get("W", 60.0))
    thickness = dims.get("thickness", dims.get("height", dims.get("T", 8.0)))
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "rectangle", "length": length, "width": width},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.PAD,
            parameters={"distance": thickness},
            depends_on=[1],
        ),
        FeatureStep(
            step=3,
            operation=FeatureOperation.FILLET,
            parameters={"radius": min(length, width) * 0.05},
            depends_on=[2],
        ),
    ]


def _shaft_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """SHAFT: length + diameter → 圆柱 + 两端倒角。"""
    length = dims.get("length", dims.get("L", 100.0))
    diameter = dims.get("diameter", dims.get("D", 20.0))
    radius = diameter / 2.0
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "circle", "radius": radius},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.PAD,
            parameters={"distance": length},
            depends_on=[1],
        ),
        FeatureStep(
            step=3,
            operation=FeatureOperation.CHAMFER,
            parameters={"size": radius * 0.1},
            depends_on=[2],
        ),
    ]


def _gear_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """GEAR: diameter + thickness + hole_diameter → 圆盘 + 中心孔。"""
    diameter = dims.get("diameter", dims.get("D", 100.0))
    thickness = dims.get("thickness", dims.get("height", dims.get("T", 20.0)))
    hole_diameter = dims.get("hole_diameter", diameter * 0.2)
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "circle", "radius": diameter / 2.0},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.PAD,
            parameters={"distance": thickness},
            depends_on=[1],
        ),
        FeatureStep(
            step=3,
            operation=FeatureOperation.HOLE,
            parameters={"diameter": hole_diameter, "depth": thickness},
            depends_on=[2],
        ),
    ]


def _housing_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """HOUSING: length×width×height → BOX + POCKET(内腔)。"""
    length = dims.get("length", dims.get("L", 200.0))
    width = dims.get("width", dims.get("W", 120.0))
    height = dims.get("height", dims.get("H", 80.0))
    wall = dims.get("wall", 5.0)
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "rectangle", "length": length, "width": width},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.PAD,
            parameters={"distance": height},
            depends_on=[1],
        ),
        FeatureStep(
            step=3,
            operation=FeatureOperation.SKETCH,
            parameters={
                "shape": "rectangle",
                "length": length - 2 * wall,
                "width": width - 2 * wall,
                "offset_x": 0,
                "offset_y": 0,
            },
        ),
        FeatureStep(
            step=4,
            operation=FeatureOperation.POCKET,
            parameters={"depth": height - wall},
            depends_on=[3, 2],
        ),
    ]


def _bracket_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """BRACKET: length×width×thickness → L形平板 + 圆角。"""
    length = dims.get("length", dims.get("L", 100.0))
    width = dims.get("width", dims.get("W", 60.0))
    thickness = dims.get("thickness", dims.get("T", 10.0))
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "L_shape", "length": length, "width": width},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.PAD,
            parameters={"distance": thickness},
            depends_on=[1],
        ),
        FeatureStep(
            step=3,
            operation=FeatureOperation.FILLET,
            parameters={"radius": thickness},
            depends_on=[2],
        ),
    ]


def _flange_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """FLANGE: diameter + thickness + hole_diameter → 圆盘 + 中心孔 + 圆周孔阵列。"""
    diameter = dims.get("diameter", dims.get("D", 100.0))
    thickness = dims.get("thickness", dims.get("T", 15.0))
    hole_diameter = dims.get("hole_diameter", diameter * 0.15)
    pcd = dims.get("pitch_circle_diameter", diameter * 0.7)
    hole_count = int(dims.get("hole_count", 6))
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "circle", "radius": diameter / 2.0},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.PAD,
            parameters={"distance": thickness},
            depends_on=[1],
        ),
        FeatureStep(
            step=3,
            operation=FeatureOperation.HOLE,
            parameters={"diameter": hole_diameter, "depth": thickness},
            depends_on=[2],
        ),
        FeatureStep(
            step=4,
            operation=FeatureOperation.PATTERN_LINEAR,
            parameters={"count": hole_count, "pcd": pcd, "hole_diameter": hole_diameter},
            depends_on=[3],
        ),
    ]


def _custom_steps(dims: dict[str, float]) -> list[FeatureStep]:
    """CUSTOM: 默认 fallback — length×width×height → BOX。"""
    length = dims.get("length", 50.0)
    width = dims.get("width", 50.0)
    height = dims.get("height", 50.0)
    return [
        FeatureStep(
            step=1,
            operation=FeatureOperation.SKETCH,
            parameters={"shape": "rectangle", "length": length, "width": width},
        ),
        FeatureStep(
            step=2,
            operation=FeatureOperation.PAD,
            parameters={"distance": height},
            depends_on=[1],
        ),
    ]


_PART_STEPS = {
    PartType.BOX: _box_steps,
    PartType.CYLINDER: _cylinder_steps,
    PartType.SPHERE: _sphere_steps,
    PartType.CONE: _cone_steps,
    PartType.TORUS: _torus_steps,
    PartType.PLATE: _plate_steps,
    PartType.SHAFT: _shaft_steps,
    PartType.GEAR: _gear_steps,
    PartType.HOUSING: _housing_steps,
    PartType.BRACKET: _bracket_steps,
    PartType.FLANGE: _flange_steps,
    PartType.CUSTOM: _custom_steps,
}


class DesignAgent:
    """设计规划Agent。

    输入：RequirementDocument（需求分析Agent输出）
    输出：ModelingPlan（特征步骤序列 + 参数化约束）

    设计策略（方法论v1.0 3.1.2节）：
    1. 按 PartType 选特征模板
    2. 步骤有序：sketch → pad/pocket → 细节特征(fillet/chamfer/hole)
    3. 参数化约束：关键尺寸保持关联，便于后续修改
    """

    def plan(self, doc: RequirementDocument) -> ModelingPlan:
        """生成建模计划。"""
        fn = _PART_STEPS.get(doc.part_type, _custom_steps)
        features = fn(doc.dimensions)
        parametric = self._build_parametric(doc)
        return ModelingPlan(
            features=features,
            connectors=doc.connectors,
            parametric_constraints=parametric,
        )

    def _build_parametric(self, doc: RequirementDocument) -> dict[str, str]:
        """提取参数化约束表达式。"""
        constraints: dict[str, str] = {}
        dims = doc.dimensions
        if "length" in dims and "width" in dims:
            constraints["aspect"] = f"width = {dims['width']} (length = {dims['length']})"
        if doc.part_type == PartType.GEAR and "diameter" in dims:
            constraints["hole"] = f"hole_diameter ≈ diameter × 0.2"
        if doc.part_type == PartType.FLANGE and "diameter" in dims:
            constraints["pattern"] = "pcd = diameter × 0.7, hole_count = 6"
        return constraints

    def to_commands(self, plan: ModelingPlan) -> list[str]:
        """将 ModelingPlan 转成 CLI 命令描述（供建模Agent使用）。"""
        out = []
        for f in plan.features:
            params = ", ".join(f"{k}={v}" for k, v in f.parameters.items())
            deps = f" (depends: {f.depends_on})" if f.depends_on else ""
            out.append(f"Step {f.step}: {f.operation.value} [{params}]{deps}")
        return out

    def connectors_from_plan(
        self, plan: ModelingPlan, part_name: str
    ) -> list[Connector]:
        """基于零件几何自动推断连接点（装配Agent使用）。"""
        if plan.connectors:
            return plan.connectors
        # 默认连接点：质心原点
        return [
            Connector(
                name=f"{part_name}_center",
                position="0,0,0",
                constraint_type="coincident",
            )
        ]
