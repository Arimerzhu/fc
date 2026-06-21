"""Part (primitive) commands.

Commands for creating and managing 3D primitive parts:
  part add       — Add a primitive (box, cylinder, sphere, cone, torus, wedge, helix)
  part remove    — Remove a part by name
  part list      — List all parts
  part get       — Get part details
  part transform — Transform position/rotation
  part boolean   — Boolean operations (cut, fuse, common)
  part copy      — Copy a part
  part mirror    — Mirror a part
  part scale     — Scale a part
  part fillet-3d — Apply 3D fillet
  part chamfer-3d — Apply 3D chamfer
  part loft      — Loft through cross-sections
  part sweep     — Sweep profile along path
  part revolve   — Revolve a part
  part extrude   — Extrude a part
  part info      — Get detailed part info
  part bounds    — Get bounding box
"""

from __future__ import annotations

import click


def _handle_error(f):
    from fc_cli.main import handle_error
    return handle_error(f)


def _get_backend():
    """获取 backend 实例（委托给 main.get_backend 统一管理）。"""
    from fc_cli.main import get_backend
    return get_backend()


@click.group("part")
def part_group():
    """3D part/primitive management commands."""
    pass


@part_group.command("add")
@click.argument("part_type", default="box")
@click.option("--name", "-n", help="Part name.")
@click.option("--position", "-pos", help="Position as x,y,z (e.g. 0,0,0).")
@click.option("--rotation", "-rot", help="Rotation as rx,ry,rz degrees.")
@click.option("--param", "-P", multiple=True, help="Param as key=value.")
@_handle_error
def part_add(part_type: str, name: str | None, position: str | None,
             rotation: str | None, param: tuple) -> None:
    """Add a 3D primitive part.

    Supported types: box, cylinder, sphere, cone, torus, wedge, helix, ellipsoid, spiral.
    """
    from fc_cli.main import _output, parse_params
    from fc_core.types import Vec3

    backend = _get_backend()
    try:
        backend.connect()
        pos = Vec3.parse(position) if position else None
        rot = Vec3.parse(rotation) if rotation else None
        params = parse_params(param)

        type_map = {
            "box": "Part::Box",
            "cylinder": "Part::Cylinder",
            "sphere": "Part::Sphere",
            "cone": "Part::Cone",
            "torus": "Part::Torus",
            "wedge": "Part::Wedge",
            "helix": "Part::Helix",
            "ellipsoid": "Part::Ellipsoid",
            "spiral": "Part::Spiral",
        }

        fc_type = type_map.get(part_type)
        if fc_type is None:
            _output.error(f"Unknown part type: {part_type}",
                         code="INVALID_TYPE",
                         suggestion=f"Supported types: {', '.join(type_map.keys())}")
            return

        obj_name = name or part_type.capitalize()
        props = params or {}

        # Set default dimensions based on type
        if part_type == "box" and not props:
            props = {"Length": 10, "Width": 10, "Height": 10}
        elif part_type == "cylinder" and not props:
            props = {"Radius": 5, "Height": 10}
        elif part_type == "sphere" and not props:
            props = {"Radius": 5}
        elif part_type == "cone" and not props:
            props = {"Radius1": 5, "Radius2": 0, "Height": 10}
        elif part_type == "torus" and not props:
            props = {"Radius1": 10, "Radius2": 2}
        elif part_type == "ellipsoid" and not props:
            props = {"Radius1": 10, "Radius2": 5, "Radius3": 3}

        if pos:
            props["Placement"] = {"Base": {"x": pos.x, "y": pos.y, "z": pos.z}}

        r = backend.object_create(fc_type, obj_name, props)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@part_group.command("remove")
@click.argument("name")
@_handle_error
def part_remove(name: str) -> None:
    """Remove a part by name."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.object_delete(name)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@part_group.command("list")
@_handle_error
def part_list() -> None:
    """List all parts in the current document."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.object_list()
        if r.status == "ok":
            objects = r.data.get("objects", r.data.get("data", {}).get("objects", []))
            _output.output(r.to_dict(), f"{len(objects)} object(s):")
        else:
            _output.output(r.to_dict())
    finally:
        backend.disconnect()


@part_group.command("get")
@click.argument("name")
@_handle_error
def part_get(name: str) -> None:
    """Get details of a part by name."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.object_get(name)
        _output.output(r.to_dict(), f"Part '{name}':")
    finally:
        backend.disconnect()


@part_group.command("transform")
@click.argument("name")
@click.option("--position", "-pos", help="New position as x,y,z.")
@click.option("--rotation", "-rot", help="New rotation as rx,ry,rz degrees.")
@_handle_error
def part_transform(name: str, position: str | None, rotation: str | None) -> None:
    """Transform a part (position and/or rotation)."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        pos = [float(x) for x in position.split(",")] if position else None
        rot = [float(x) for x in rotation.split(",")] if rotation else None

        code_lines = [
            'import FreeCAD',
            'doc = FreeCAD.ActiveDocument',
            f'obj = doc.getObject("{name}")',
            f'if obj is None:',
            f'    raise ValueError(f"Object \'{name}\' not found")',
        ]
        if pos:
            code_lines.append(
                f'obj.Placement.Base = FreeCAD.Vector({pos[0]}, {pos[1]}, {pos[2]})'
            )
        if rot:
            code_lines.append(
                f'obj.Placement.Rotation = FreeCAD.Rotation({rot[0]}, {rot[1]}, {rot[2]})'
            )
        code_lines.append('doc.recompute()')

        r = backend.execute_code("\n".join(code_lines))
        _output.output(r.to_dict(), r.message or f"Transformed: {name}")
    finally:
        backend.disconnect()


@part_group.command("boolean")
@click.argument("operation", type=click.Choice(["cut", "fuse", "common"]))
@click.argument("base")
@click.argument("tool")
@click.option("--name", "-n", help="Name for result.")
@_handle_error
def part_boolean(operation: str, base: str, tool: str, name: str | None) -> None:
    """Perform boolean operation on two parts.

    Operations: cut, fuse, common
    """
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        if operation == "cut":
            r = backend.boolean_cut(base, tool, name or "Cut")
        elif operation == "fuse":
            r = backend.boolean_union(base, tool, name or "Fusion")
        else:
            r = backend.boolean_common(base, tool, name or "Common")
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@part_group.command("copy")
@click.argument("name")
@click.option("--name", "-n", "copy_name", help="Name for copy.")
@_handle_error
def part_copy(name: str, copy_name: str | None) -> None:
    """Copy a part by name."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        new_name = copy_name or f"{name}_Copy"
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if hasattr(obj, "Shape"):
    result = doc.addObject("Part::Feature", "{new_name}")
    result.Shape = obj.Shape.copy()
    doc.recompute()
else:
    raise ValueError("Object has no Shape")
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Copied: {name} → {new_name}")
    finally:
        backend.disconnect()


@part_group.command("mirror")
@click.argument("name")
@click.option("--plane", default="XY", type=click.Choice(["XY", "XZ", "YZ"]),
              help="Mirror plane.")
@click.option("--name", "-n", "result_name", help="Name for result.")
@_handle_error
def part_mirror(name: str, plane: str, result_name: str | None) -> None:
    """Create a mirrored copy of a part."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.mirror_object(name, plane, result_name or f"{name}_Mirrored")
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@part_group.command("scale")
@click.argument("name")
@click.argument("factor", type=str)
@click.option("--name", "-n", "result_name", help="Name for result.")
@_handle_error
def part_scale(name: str, factor: str, result_name: str | None) -> None:
    """Scale a part by a uniform factor or x,y,z factors."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        if "," in factor:
            f = [float(x.strip()) for x in factor.split(",")]
        else:
            f = float(factor)
        r = backend.scale_object(name, f, result_name or f"{name}_Scaled")
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@part_group.command("fillet-3d")
@click.argument("name")
@click.option("--radius", "-r", default=1.0, type=float, help="Fillet radius.")
@click.option("--edges", default="all", help="Edges: 'all' or comma-sep indices.")
@click.option("--name", "-n", "result_name", help="Name for result.")
@_handle_error
def part_fillet_3d(name: str, radius: float, edges: str,
                   result_name: str | None) -> None:
    """Apply a 3D fillet to a part."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        edge_list = None if edges == "all" else [int(x) for x in edges.split(",")]
        r = backend.fillet_edges(name, radius, edge_list, result_name or "Fillet")
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@part_group.command("chamfer-3d")
@click.argument("name")
@click.option("--size", "-s", default=1.0, type=float, help="Chamfer size.")
@click.option("--edges", default="all", help="Edges: 'all' or comma-sep indices.")
@click.option("--name", "-n", "result_name", help="Name for result.")
@_handle_error
def part_chamfer_3d(name: str, size: float, edges: str,
                    result_name: str | None) -> None:
    """Apply a 3D chamfer to a part."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        edge_list = None if edges == "all" else [int(x) for x in edges.split(",")]
        r = backend.chamfer_edges(name, size, edge_list, result_name or "Chamfer")
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@part_group.command("info")
@click.argument("name")
@_handle_error
def part_info(name: str) -> None:
    """Get detailed information about a part."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.object_get(name)
        _output.output(r.to_dict(), f"Part '{name}' info:")
    finally:
        backend.disconnect()


@part_group.command("bounds")
@click.argument("name")
@_handle_error
def part_bounds(name: str) -> None:
    """Get bounding box for a part."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if hasattr(obj, "Shape") and obj.Shape:
    bb = obj.Shape.BoundBox
    _fc_result = {{
        "status": "ok",
        "data": {{
            "x_min": bb.XMin, "x_max": bb.XMax,
            "y_min": bb.YMin, "y_max": bb.YMax,
            "z_min": bb.ZMin, "z_max": bb.ZMax,
            "dimensions": [bb.XLength, bb.YLength, bb.ZLength],
            "diagonal": bb.DiagonalLength,
        }},
        "message": ""
    }}
else:
    _fc_result = {{"status": "error", "data": {{}}, "message": "Object has no Shape"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"Part '{name}' bounds:")
    finally:
        backend.disconnect()


@part_group.command("hole")
@click.argument("name")
@click.option("--diameter", "-d", default=5.0, type=float, help="Hole diameter.")
@click.option("--depth", default=10.0, type=float, help="Hole depth.")
@click.option("--position", "-pos", help="Position as x,y,z.")
@click.option("--direction", default="0,0,1", help="Hole direction as x,y,z.")
@click.option("--name", "-n", "result_name", help="Name for result.")
@_handle_error
def part_hole(name: str, diameter: float, depth: float,
              position: str | None, direction: str,
              result_name: str | None) -> None:
    """Create a hole through a part."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        dx, dy, dz = [float(x) for x in direction.split(",")]
        px, py, pz = [float(x) for x in position.split(",")] if position else (0, 0, 0)
        out_name = result_name or f"{name}_Hole"
        radius = diameter / 2.0
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if not hasattr(obj, "Shape") or not obj.Shape:
    raise ValueError(f"Object '{name}' has no Shape")
# Create a cylinder for the hole
hole_cyl = Part.makeCylinder({radius}, {depth}, FreeCAD.Vector({px}, {py}, {pz}), FreeCAD.Vector({dx}, {dy}, {dz}))
result = doc.addObject("Part::Feature", "{out_name}")
result.Shape = obj.Shape.cut(hole_cyl)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created hole: {out_name} (diameter={diameter}mm)")
    finally:
        backend.disconnect()
