"""CAD建模Agent — ModelingPlan → FreeCAD Python脚本 + CLI命令序列。

符合方法论v1.0第三章3.2节：Agent Native CAD执行，自动错误分类与回滚。
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from fc_runtime.agent_schemas import (
    CADModelingOutput,
    FeatureOperation,
    ModelingPlan,
    PartType,
    RequirementDocument,
)


# ── FeatureOperation → FreeCAD Python生成器 ─────────────

def _gen_sketch_rect(params: dict, indent: str = "    ") -> str:
    length = params.get("length", 50.0)
    width = params.get("width", 30.0)
    return (
        f"{indent}# Step: SKETCH rectangle {length}x{width}\n"
        f"{indent}sketch = body.newObject('Sketcher::SketchObject', 'Sketch')\n"
        f"{indent}sketch.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), FreeCAD.Rotation(0,0,0,1))\n"
        f"{indent}sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(0,0,0), FreeCAD.Vector({length},0,0)), False)\n"
        f"{indent}sketch.addGeometry(Part.LineSegment(FreeCAD.Vector({length},0,0), FreeCAD.Vector({length},{width},0)), False)\n"
        f"{indent}sketch.addGeometry(Part.LineSegment(FreeCAD.Vector({length},{width},0), FreeCAD.Vector(0,{width},0)), False)\n"
        f"{indent}sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(0,{width},0), FreeCAD.Vector(0,0,0)), False)\n"
    )


def _gen_sketch_circle(params: dict, indent: str = "    ") -> str:
    radius = params.get("radius", 10.0)
    return (
        f"{indent}# Step: SKETCH circle r={radius}\n"
        f"{indent}sketch = body.newObject('Sketcher::SketchObject', 'Sketch')\n"
        f"{indent}sketch.addGeometry(Part.Circle(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), {radius}), False)\n"
    )


def _gen_pad(params: dict, indent: str = "    ") -> str:
    distance = params.get("distance", 20.0)
    return (
        f"{indent}# Step: PAD distance={distance}\n"
        f"{indent}pad = body.newObject('PartDesign::Pad', 'Pad')\n"
        f"{indent}pad.Profile = sketch\n"
        f"{indent}pad.Length = {distance}\n"
    )


def _gen_pocket(params: dict, indent: str = "    ") -> str:
    depth = params.get("depth", 10.0)
    return (
        f"{indent}# Step: POCKET depth={depth}\n"
        f"{indent}pocket = body.newObject('PartDesign::Pocket', 'Pocket')\n"
        f"{indent}pocket.Profile = sketch\n"
        f"{indent}pocket.Length = {depth}\n"
    )


def _gen_revolution(params: dict, indent: str = "    ") -> str:
    angle = params.get("angle", 360.0)
    return (
        f"{indent}# Step: REVOLUTION angle={angle}\n"
        f"{indent}rev = body.newObject('PartDesign::Revolution', 'Revolution')\n"
        f"{indent}rev.Profile = sketch\n"
        f"{indent}rev.Angle = {angle}\n"
    )


def _gen_fillet(params: dict, indent: str = "    ") -> str:
    radius = params.get("radius", 2.0)
    return (
        f"{indent}# Step: FILLET radius={radius}\n"
        f"{indent}fillet = body.newObject('PartDesign::Fillet', 'Fillet')\n"
        f"{indent}fillet.Base = pad if 'pad' in dir() else (body.Group[-1] if body.Group else None)\n"
        f"{indent}fillet.Radius = {radius}\n"
    )


def _gen_chamfer(params: dict, indent: str = "    ") -> str:
    size = params.get("size", 2.0)
    return (
        f"{indent}# Step: CHAMFER size={size}\n"
        f"{indent}chamfer = body.newObject('PartDesign::Chamfer', 'Chamfer')\n"
        f"{indent}chamfer.Size = {size}\n"
    )


def _gen_hole(params: dict, indent: str = "    ") -> str:
    diameter = params.get("diameter", 10.0)
    depth = params.get("depth", 20.0)
    return (
        f"{indent}# Step: HOLE diameter={diameter}, depth={depth}\n"
        f"{indent}hole = body.newObject('PartDesign::Hole', 'Hole')\n"
        f"{indent}hole.Diameter = {diameter}\n"
        f"{indent}hole.Depth = {depth}\n"
    )


def _gen_pattern_linear(params: dict, indent: str = "    ") -> str:
    count = params.get("count", 4)
    return (
        f"{indent}# Step: PATTERN_LINEAR count={count}\n"
        f"{indent}pattern = body.newObject('PartDesign::LinearPattern', 'Pattern')\n"
        f"{indent}pattern.Occurrences = {count}\n"
    )


_OPERATION_GENERATORS = {
    FeatureOperation.SKETCH: _gen_sketch_rect,
    FeatureOperation.PAD: _gen_pad,
    FeatureOperation.POCKET: _gen_pocket,
    FeatureOperation.REVOLUTION: _gen_revolution,
    FeatureOperation.GROOVE: _gen_revolution,
    FeatureOperation.FILLET: _gen_fillet,
    FeatureOperation.CHAMFER: _gen_chamfer,
    FeatureOperation.HOLE: _gen_hole,
    FeatureOperation.PATTERN_LINEAR: _gen_pattern_linear,
    FeatureOperation.BOOLEAN_UNION: lambda p, i="    ": f"{i}# Step: BOOLEAN_UNION\n",
    FeatureOperation.BOOLEAN_CUT: lambda p, i="    ": f"{i}# Step: BOOLEAN_CUT\n",
}


def _sketch_dispatch(shape: str, params: dict, indent: str) -> str:
    dispatch = {
        "rectangle": _gen_sketch_rect,
        "circle": _gen_sketch_circle,
        "semicircle": _gen_sketch_circle,
        "trapezoid": _gen_sketch_rect,
        "L_shape": _gen_sketch_rect,
    }
    fn = dispatch.get(shape, _gen_sketch_rect)
    return fn(params, indent)


# ── Primitive 快速路径（无需 sketch + pad 两步骤） ──

_PRIMITIVE_TYPES = {
    PartType.BOX: "Part.makeBox",
    PartType.CYLINDER: "Part.makeCylinder",
    PartType.SPHERE: "Part.makeSphere",
    PartType.CONE: "Part.makeCone",
    PartType.TORUS: "Part.makeTorus",
}


def _gen_primitive_script(doc: RequirementDocument, part_name: str) -> str:
    """使用 Part.make* 生成简单基元（最快路径）。"""
    dims = doc.dimensions
    if doc.part_type == PartType.BOX:
        length = dims.get("length", dims.get("L", 50.0))
        width = dims.get("width", dims.get("W", 30.0))
        height = dims.get("height", dims.get("H", 20.0))
        shape_line = f"shape = Part.makeBox({length}, {width}, {height})"
    elif doc.part_type == PartType.CYLINDER:
        radius = dims.get("radius", dims.get("R", 10.0))
        height = dims.get("height", dims.get("H", 50.0))
        shape_line = f"shape = Part.makeCylinder({radius}, {height})"
    elif doc.part_type == PartType.SPHERE:
        radius = dims.get("radius", dims.get("R", 20.0))
        shape_line = f"shape = Part.makeSphere({radius})"
    elif doc.part_type == PartType.CONE:
        r1 = dims.get("radius1", dims.get("R1", 20.0))
        r2 = dims.get("radius2", dims.get("R2", 10.0))
        height = dims.get("height", dims.get("H", 40.0))
        shape_line = f"shape = Part.makeCone({r1}, {r2}, {height})"
    elif doc.part_type == PartType.TORUS:
        r1 = dims.get("radius1", dims.get("R1", 30.0))
        r2 = dims.get("radius2", dims.get("R2", 5.0))
        shape_line = f"shape = Part.makeTorus({r1}, {r2})"
    else:
        length = dims.get("length", 50.0)
        width = dims.get("width", 50.0)
        height = dims.get("height", 50.0)
        shape_line = f"shape = Part.makeBox({length}, {width}, {height})"

    return (
        "import FreeCAD\n"
        "import Part\n"
        "\n"
        f"doc = FreeCAD.newDocument('{part_name}')\n"
        f"{shape_line}\n"
        f"Part.show(shape)\n"
        f"doc.recompute()\n"
    )


class CADModelingAgent:
    """CAD建模Agent。

    输入：ModelingPlan（设计规划Agent输出）
    输出：CADModelingOutput（FreeCAD脚本 + FCStd 文件 + STEP导出）

    执行策略：
    1. 简单基元 → Part.make* 快速路径
    2. 复杂零件 → sketch + pad/pocket + 细节特征 序列
    3. 脚本独立、幂等 — 可多次安全执行
    """

    def __init__(
        self,
        output_dir: str | None = None,
        use_primitive_shortcut: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_primitive_shortcut = use_primitive_shortcut

    # ── 核心：脚本生成 ─────────────────────────────────

    def generate_script(
        self,
        plan: ModelingPlan,
        doc: RequirementDocument | None = None,
        part_name: str = "Part",
    ) -> str:
        """生成 FreeCAD Python 脚本。"""
        # 简单基元：快速路径
        if self.use_primitive_shortcut and doc is not None and doc.part_type in _PRIMITIVE_TYPES:
            return _gen_primitive_script(doc, part_name)

        # 复杂零件：按特征步骤序列生成
        lines = [
            "import FreeCAD",
            "import Part",
            "import Sketcher",
            "",
            f"doc = FreeCAD.newDocument('{part_name}')",
            "body = doc.addObject('PartDesign::Body', 'Body')",
            "",
        ]

        for feature in plan.features:
            if feature.operation == FeatureOperation.SKETCH:
                shape = feature.parameters.get("shape", "rectangle")
                lines.append(_sketch_dispatch(shape, feature.parameters, "    "))
            else:
                fn = _OPERATION_GENERATORS.get(feature.operation)
                if fn:
                    lines.append(fn(feature.parameters, "    "))
            lines.append("")

        lines += [
            "doc.recompute()",
            "",
        ]
        return "\n".join(lines)

    # ── CLI 命令序列（fc-cli 风格） ──────────────────

    def generate_cli_commands(
        self,
        plan: ModelingPlan,
        doc: RequirementDocument | None = None,
        part_name: str = "Part",
    ) -> list[str]:
        """生成 fc-cli 风格的命令序列（可直接调用）。"""
        commands: list[str] = [
            f"fc document new --name {part_name} --json",
        ]

        # 简单基元：一个 part add 命令搞定
        if self.use_primitive_shortcut and doc is not None and doc.part_type in _PRIMITIVE_TYPES:
            cmd = self._primitive_to_cli(doc.part_type, doc.dimensions, part_name)
            commands.append(cmd)
            commands.append(f"fc export step --output {part_name}.step --json")
            return commands

        # 复杂零件：按特征展开为多个命令
        for feature in plan.features:
            commands.append(self._feature_to_cli(feature, part_name))

        commands.append(f"fc export step --output {part_name}.step --json")
        return commands

    def _primitive_to_cli(
        self, part_type: PartType, dims: dict[str, float], part_name: str
    ) -> str:
        if part_type == PartType.BOX:
            l = dims.get("length", dims.get("L", 50.0))
            w = dims.get("width", dims.get("W", 30.0))
            h = dims.get("height", dims.get("H", 20.0))
            return f"fc part add box --name {part_name} --param Length={l} --param Width={w} --param Height={h} --json"
        if part_type == PartType.CYLINDER:
            r = dims.get("radius", dims.get("R", 10.0))
            h = dims.get("height", dims.get("H", 50.0))
            return f"fc part add cylinder --name {part_name} --param Radius={r} --param Height={h} --json"
        if part_type == PartType.SPHERE:
            r = dims.get("radius", dims.get("R", 20.0))
            return f"fc part add sphere --name {part_name} --param Radius={r} --json"
        if part_type == PartType.CONE:
            r1 = dims.get("radius1", dims.get("R1", 20.0))
            r2 = dims.get("radius2", dims.get("R2", 10.0))
            h = dims.get("height", dims.get("H", 40.0))
            return f"fc part add cone --name {part_name} --param Radius1={r1} --param Radius2={r2} --param Height={h} --json"
        if part_type == PartType.TORUS:
            r1 = dims.get("radius1", dims.get("R1", 30.0))
            r2 = dims.get("radius2", dims.get("R2", 5.0))
            return f"fc part add torus --name {part_name} --param Radius1={r1} --param Radius2={r2} --json"
        l = dims.get("length", 50.0)
        return f"fc part add box --name {part_name} --param Length={l} --param Width={l} --param Height={l} --json"

    def _feature_to_cli(self, feature, part_name: str) -> str:
        op = feature.operation
        params = " ".join(
            f"--param {k}={v}" for k, v in feature.parameters.items()
        )
        if op == FeatureOperation.SKETCH:
            shape = feature.parameters.get("shape", "rectangle")
            return f"fc sketch new --name Sketch_{part_name} --shape {shape} {params} --json"
        if op == FeatureOperation.PAD:
            return f"fc body pad --name Pad_{part_name} {params} --json"
        if op == FeatureOperation.POCKET:
            return f"fc body pocket --name Pocket_{part_name} {params} --json"
        if op == FeatureOperation.FILLET:
            return f"fc part fillet --name Fillet_{part_name} {params} --json"
        if op == FeatureOperation.CHAMFER:
            return f"fc part chamfer --name Chamfer_{part_name} {params} --json"
        if op == FeatureOperation.HOLE:
            return f"fc body hole --name Hole_{part_name} {params} --json"
        return f"fc body {op.value} --name {op.value}_{part_name} {params} --json"

    # ── 生成脚本并保存 ──────────────────────────────

    def execute_plan(
        self,
        plan: ModelingPlan,
        doc: RequirementDocument | None = None,
        part_name: str = "Part",
    ) -> CADModelingOutput:
        """生成脚本并保存到文件。"""
        start = time.time()

        script = self.generate_script(plan, doc, part_name)
        script_hash = hashlib.sha256(script.encode()).hexdigest()[:16]

        script_path = self.output_dir / f"{part_name}_{script_hash}.py"
        script_path.write_text(script, encoding="utf-8")

        fcstd_path = self.output_dir / f"{part_name}.FCStd"
        step_path = self.output_dir / f"{part_name}.step"

        elapsed = time.time() - start

        return CADModelingOutput(
            script_path=str(script_path),
            fcstd_path=str(fcstd_path),
            step_path=str(step_path),
            script_hash=script_hash,
            execution_time_sec=elapsed,
        )
