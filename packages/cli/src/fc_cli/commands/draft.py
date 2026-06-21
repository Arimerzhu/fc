"""Draft commands.

Commands for Draft workbench operations:
  draft line        — Create a line
  draft wire        — Create a wire/polyline
  draft circle      — Create a circle
  draft arc         — Create an arc
  draft rect        — Create a rectangle
  draft polygon     — Create a regular polygon
  draft text        — Create text
  draft dimension   — Create a dimension
  draft array       — Create an array
  draft offset      — Create an offset
  draft move        — Move an object
  draft rotate      — Rotate an object
  draft scale       — Scale an object
  draft trim        — Trim/extend geometry
  draft list        — List all Draft objects
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click


def _handle_error(f):
    from fc_cli.main import handle_error
    return handle_error(f)


def _get_backend():
    """获取 backend 实例（委托给 main.get_backend 统一管理）。"""
    from fc_cli.main import get_backend
    return get_backend()


@click.group("draft")
def draft_group():
    """Draft workbench commands."""
    pass


@draft_group.command("line")
@click.option("--start", "-s", default="0,0,0", help="Start point as x,y,z.")
@click.option("--end", "-e", default="10,0,0", help="End point as x,y,z.")
@click.option("--name", "-n", help="Object name.")
@_handle_error
def draft_line(start: str, end: str, name: str | None) -> None:
    """Create a line."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        sx, sy, sz = [float(x) for x in start.split(",")]
        ex, ey, ez = [float(x) for x in end.split(",")]
        obj_name = name or "Line"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
p1 = FreeCAD.Vector({sx}, {sy}, {sz})
p2 = FreeCAD.Vector({ex}, {ey}, {ez})
obj = Draft.make_line(p1, p2)
obj.Label = "{obj_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created line: {obj_name}")
    finally:
        backend.disconnect()


@draft_group.command("wire")
@click.option("--points", "-p", required=True,
              help="Points as semicolon-separated x,y,z coordinates.")
@click.option("--closed/--open", default=False, help="Close the wire.")
@click.option("--name", "-n", help="Object name.")
@_handle_error
def draft_wire(points: str, closed: bool, name: str | None) -> None:
    """Create a wire/polyline."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        pts = []
        for pt_str in points.split(";"):
            pt_str = pt_str.strip()
            if pt_str:
                coords = [float(x) for x in pt_str.split(",")]
                pts.append(f"FreeCAD.Vector({coords[0]}, {coords[1]}, {coords[2]})")
        points_list = ", ".join(pts)
        obj_name = name or "Wire"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
points = [{points_list}]
obj = Draft.make_wire(points, closed={closed})
obj.Label = "{obj_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created wire: {obj_name}")
    finally:
        backend.disconnect()


@draft_group.command("circle")
@click.option("--center", "-c", default="0,0,0", help="Center as x,y,z.")
@click.option("--radius", "-r", default=5.0, type=float, help="Radius.")
@click.option("--name", "-n", help="Object name.")
@_handle_error
def draft_circle(center: str, radius: float, name: str | None) -> None:
    """Create a circle."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy, cz = [float(x) for x in center.split(",")]
        obj_name = name or "Circle"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
center = FreeCAD.Vector({cx}, {cy}, {cz})
obj = Draft.make_circle({radius}, center=center)
obj.Label = "{obj_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created circle: {obj_name}")
    finally:
        backend.disconnect()


@draft_group.command("arc")
@click.option("--center", "-c", default="0,0,0", help="Center as x,y,z.")
@click.option("--radius", "-r", default=5.0, type=float, help="Radius.")
@click.option("--start-angle", default=0.0, type=float, help="Start angle (deg).")
@click.option("--end-angle", default=90.0, type=float, help="End angle (deg).")
@click.option("--name", "-n", help="Object name.")
@_handle_error
def draft_arc(center: str, radius: float, start_angle: float,
              end_angle: float, name: str | None) -> None:
    """Create an arc."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy, cz = [float(x) for x in center.split(",")]
        obj_name = name or "Arc"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
center = FreeCAD.Vector({cx}, {cy}, {cz})
obj = Draft.make_arc({radius}, {start_angle}, {end_angle}, center=center)
obj.Label = "{obj_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created arc: {obj_name}")
    finally:
        backend.disconnect()


@draft_group.command("rect")
@click.option("--corner", default="0,0,0", help="Corner as x,y,z.")
@click.option("--width", "-w", default=10.0, type=float, help="Width.")
@click.option("--height", "-h", default=10.0, type=float, help="Height.")
@click.option("--name", "-n", help="Object name.")
@_handle_error
def draft_rect(corner: str, width: float, height: float,
               name: str | None) -> None:
    """Create a rectangle."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy, cz = [float(x) for x in corner.split(",")]
        obj_name = name or "Rectangle"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
p1 = FreeCAD.Vector({cx}, {cy}, {cz})
p2 = FreeCAD.Vector({cx + width}, {cy + height}, {cz})
obj = Draft.make_rectangle({width}, {height}, placement=FreeCAD.Placement(p1, FreeCAD.Rotation()))
obj.Label = "{obj_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created rectangle: {obj_name}")
    finally:
        backend.disconnect()


@draft_group.command("polygon")
@click.option("--center", "-c", default="0,0,0", help="Center as x,y,z.")
@click.option("--radius", "-r", default=5.0, type=float, help="Radius.")
@click.option("--sides", "-s", default=6, type=int, help="Number of sides.")
@click.option("--name", "-n", help="Object name.")
@_handle_error
def draft_polygon(center: str, radius: float, sides: int,
                  name: str | None) -> None:
    """Create a regular polygon."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy, cz = [float(x) for x in center.split(",")]
        obj_name = name or "Polygon"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
center = FreeCAD.Vector({cx}, {cy}, {cz})
placement = FreeCAD.Placement(center, FreeCAD.Rotation())
obj = Draft.make_polygon({sides}, radius={radius}, inscribed=False, placement=placement)
obj.Label = "{obj_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created polygon: {obj_name}")
    finally:
        backend.disconnect()


@draft_group.command("text")
@click.argument("text")
@click.option("--position", "-pos", default="0,0,0", help="Position as x,y,z.")
@click.option("--size", default=10.0, type=float, help="Text size.")
@click.option("--name", "-n", help="Object name.")
@_handle_error
def draft_text(text: str, position: str, size: float,
               name: str | None) -> None:
    """Create text."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py, pz = [float(x) for x in position.split(",")]
        obj_name = name or "Text"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
pos = FreeCAD.Vector({px}, {py}, {pz})
obj = Draft.make_text("{text}", pos)
obj.Label = "{obj_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created text: {obj_name}")
    finally:
        backend.disconnect()


@draft_group.command("dimension")
@click.option("--start", "-s", required=True, help="Start point as x,y,z.")
@click.option("--end", "-e", required=True, help="End point as x,y,z.")
@click.option("--offset", "-o", default="5,5,0", help="Offset as x,y,z.")
@click.option("--name", "-n", help="Object name.")
@_handle_error
def draft_dimension(start: str, end: str, offset: str,
                    name: str | None) -> None:
    """Create a dimension."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        sx, sy, sz = [float(x) for x in start.split(",")]
        ex, ey, ez = [float(x) for x in end.split(",")]
        ox, oy, oz = [float(x) for x in offset.split(",")]
        obj_name = name or "Dimension"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
p1 = FreeCAD.Vector({sx}, {sy}, {sz})
p2 = FreeCAD.Vector({ex}, {ey}, {ez})
offset = FreeCAD.Vector({ox}, {oy}, {oz})
obj = Draft.make_dimension(p1, p2, offset)
obj.Label = "{obj_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created dimension: {obj_name}")
    finally:
        backend.disconnect()


@draft_group.command("array")
@click.argument("name")
@click.option("--type", "array_type", default="polar",
              type=click.Choice(["polar", "rectangular"]),
              help="Array type: polar or rectangular.")
@click.option("--count", "-c", default=6, type=int, help="Number of items (polar).")
@click.option("--angle", default=360.0, type=float, help="Total angle (polar, deg).")
@click.option("--rows", default=2, type=int, help="Number of rows (rectangular).")
@click.option("--cols", default=2, type=int, help="Number of columns (rectangular).")
@click.option("--row-spacing", default=10.0, type=float, help="Row spacing (rectangular).")
@click.option("--col-spacing", default=10.0, type=float, help="Column spacing (rectangular).")
@click.option("--center", "-ctr", default="0,0,0", help="Center as x,y,z (polar).")
@_handle_error
def draft_array(name: str, array_type: str, count: int, angle: float,
                rows: int, cols: int, row_spacing: float,
                col_spacing: float, center: str) -> None:
    """Create a polar or rectangular array."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy, cz = [float(x) for x in center.split(",")]
        if array_type == "polar":
            code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
center = FreeCAD.Vector({cx}, {cy}, {cz})
array = Draft.make_polar_array(obj, {count}, {angle}, center)
doc.recompute()
"""
        else:
            code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
array = Draft.make_rectangular_array(obj, {cols}, {rows}, {col_spacing}, {row_spacing})
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created {array_type} array from: {name}")
    finally:
        backend.disconnect()


@draft_group.command("offset")
@click.argument("name")
@click.option("--distance", "-d", default=2.0, type=float, help="Offset distance.")
@click.option("--name", "-n", "result_name", help="Result object name.")
@_handle_error
def draft_offset(name: str, distance: float, result_name: str | None) -> None:
    """Create an offset of an object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Offset"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
offset_obj = Draft.offset(obj, FreeCAD.Vector({distance}, 0, 0))
offset_obj.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created offset: {out_name}")
    finally:
        backend.disconnect()


@draft_group.command("move")
@click.argument("name")
@click.option("--vector", "-v", required=True, help="Move vector as x,y,z.")
@_handle_error
def draft_move(name: str, vector: str) -> None:
    """Move an object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        vx, vy, vz = [float(x) for x in vector.split(",")]
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
Draft.move(obj, FreeCAD.Vector({vx}, {vy}, {vz}))
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Moved: {name}")
    finally:
        backend.disconnect()


@draft_group.command("rotate")
@click.argument("name")
@click.option("--angle", "-a", required=True, type=float, help="Rotation angle (deg).")
@click.option("--center", "-c", default="0,0,0", help="Rotation center as x,y,z.")
@_handle_error
def draft_rotate(name: str, angle: float, center: str) -> None:
    """Rotate an object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy, cz = [float(x) for x in center.split(",")]
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
center_vec = FreeCAD.Vector({cx}, {cy}, {cz})
Draft.rotate(obj, {angle}, center_vec)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Rotated: {name}")
    finally:
        backend.disconnect()


@draft_group.command("scale")
@click.argument("name")
@click.option("--factor", "-f", required=True, type=float, help="Scale factor.")
@click.option("--center", "-c", default="0,0,0", help="Scale center as x,y,z.")
@_handle_error
def draft_scale(name: str, factor: float, center: str) -> None:
    """Scale an object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy, cz = [float(x) for x in center.split(",")]
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
center_vec = FreeCAD.Vector({cx}, {cy}, {cz})
Draft.scale(obj, FreeCAD.Vector({factor}, {factor}, {factor}), center_vec)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Scaled: {name}")
    finally:
        backend.disconnect()


@draft_group.command("trim")
@click.argument("name")
@click.option("--edge", help="Edge object name.")
@click.option("--point", "-p", help="Trim point as x,y,z.")
@_handle_error
def draft_trim(name: str, edge: str | None, point: str | None) -> None:
    """Trim/extend geometry."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py, pz = [float(x) for x in point.split(",")] if point else (0, 0, 0)
        edge_code = f'doc.getObject("{edge}")' if edge else "None"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
edge_obj = {edge_code}
trim_point = FreeCAD.Vector({px}, {py}, {pz})
Draft.trim(obj, edge_obj, trim_point)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Trimmed: {name}")
    finally:
        backend.disconnect()


@draft_group.command("list")
@_handle_error
def draft_list() -> None:
    """List all Draft objects."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = """\
import FreeCAD
doc = FreeCAD.ActiveDocument
draft_types = (
    "DraftObject", "Wire", "Circle", "Arc", "Rectangle",
    "Polygon", "Text", "Dimension", "FeaturePython",
)
draft_objects = [
    obj for obj in doc.Objects
    if hasattr(obj, "Proxy") and obj.Proxy is not None
    and type(obj.Proxy).__name__ in draft_types
]
objects_data = [{"name": o.Name, "label": o.Label, "type": o.TypeId} for o in draft_objects]
_fc_result = {
    "status": "ok",
    "data": {"objects": objects_data, "count": len(draft_objects)},
    "message": ""
}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"{r.data.get('data', {}).get('count', 0)} Draft object(s):")
    finally:
        backend.disconnect()


@draft_group.command("clone")
@click.argument("name")
@click.option("--name", "-n", "clone_name", help="Clone name.")
@_handle_error
def draft_clone(name: str, clone_name: str | None) -> None:
    """Clone a Draft object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = clone_name or f"{name}_Clone"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
clone = Draft.clone(obj)
clone.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Cloned: {name} -> {out_name}")
    finally:
        backend.disconnect()


@draft_group.command("mirror")
@click.argument("name")
@click.option("--axis", default="X", type=click.Choice(["X", "Y", "Z"]),
              help="Mirror axis.")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_mirror(name: str, axis: str, result_name: str | None) -> None:
    """Mirror a Draft object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Mirrored"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if "{axis}" == "X":
    axis_vec = FreeCAD.Vector(1, 0, 0)
elif "{axis}" == "Y":
    axis_vec = FreeCAD.Vector(0, 1, 0)
else:
    axis_vec = FreeCAD.Vector(0, 0, 1)
mirrored = Draft.mirror(obj, FreeCAD.Vector(0, 0, 0), axis_vec)
mirrored.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Mirrored: {name} -> {out_name} (axis={axis})")
    finally:
        backend.disconnect()


@draft_group.command("stretch")
@click.argument("name")
@click.option("--vector", "-v", required=True, help="Stretch vector as x,y,z.")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_stretch(name: str, vector: str, result_name: str | None) -> None:
    """Stretch a Draft object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        vx, vy, vz = [float(x) for x in vector.split(",")]
        out_name = result_name or f"{name}_Stretched"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
Draft.move(obj, FreeCAD.Vector({vx}, {vy}, {vz}))
obj.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Stretched: {name} -> {out_name}")
    finally:
        backend.disconnect()


@draft_group.command("upgrade")
@click.argument("name")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_upgrade(name: str, result_name: str | None) -> None:
    """Upgrade a Draft object (line->wire->face->shell->solid)."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Upgraded"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
upgraded = Draft.upgrade([obj], delete=True)
if upgraded and len(upgraded) > 0:
    upgraded[0].Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Upgraded: {name} -> {out_name}")
    finally:
        backend.disconnect()


@draft_group.command("downgrade")
@click.argument("name")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_downgrade(name: str, result_name: str | None) -> None:
    """Downgrade a Draft object (solid->shell->face->wire->line)."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Downgraded"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
downgraded = Draft.downgrade([obj], delete=True)
if downgraded and len(downgraded) > 0:
    downgraded[0].Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Downgraded: {name} -> {out_name}")
    finally:
        backend.disconnect()


@draft_group.command("path-array")
@click.argument("name")
@click.argument("path_name")
@click.option("--count", "-c", default=5, type=int, help="Number of items.")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_path_array(name: str, path_name: str, count: int,
                     result_name: str | None) -> None:
    """Create a path array along a wire/edge."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_PathArray"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
path_obj = doc.getObject("{path_name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if path_obj is None:
    raise ValueError(f"Path object '{path_name}' not found")
array = Draft.make_path_array(obj, path_obj, {count})
array.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created path array: {out_name} ({count} items)")
    finally:
        backend.disconnect()


@draft_group.command("point-array")
@click.argument("name")
@click.argument("points_name")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_point_array(name: str, points_name: str, result_name: str | None) -> None:
    """Create a point array at specified points."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_PointArray"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
points_obj = doc.getObject("{points_name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if points_obj is None:
    raise ValueError(f"Points object '{points_name}' not found")
array = Draft.make_point_array(obj, [points_obj])
array.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created point array: {out_name}")
    finally:
        backend.disconnect()


@draft_group.command("point")
@click.option("--position", "-p", default="0,0,0", help="Position as x,y,z.")
@click.option("--name", "-n", help="Object name.")
@_handle_error
def draft_point(position: str, name: str | None) -> None:
    """Create a point."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py, pz = [float(x) for x in position.split(",")]
        obj_name = name or "Point"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
pt = Draft.make_point(FreeCAD.Vector({px}, {py}, {pz}))
pt.Label = "{obj_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created point: {obj_name}")
    finally:
        backend.disconnect()


@draft_group.command("facebinder")
@click.argument("name")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_facebinder(name: str, result_name: str | None) -> None:
    """Create a facebinder from selected faces."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Facebinder"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
fb = Draft.make_facebinder([obj])
fb.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created facebinder: {out_name}")
    finally:
        backend.disconnect()


@draft_group.command("label")
@click.argument("target_name")
@click.option("--text", "-t", required=True, help="Label text.")
@click.option("--position", "-p", default="0,0,0", help="Position as x,y,z.")
@click.option("--name", "-n", help="Label name.")
@_handle_error
def draft_label(target_name: str, text: str, position: str,
                name: str | None) -> None:
    """Create a label pointing to an object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py, pz = [float(x) for x in position.split(",")]
        label_name = name or "Label"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
target = doc.getObject("{target_name}")
if target is None:
    raise ValueError(f"Target '{target_name}' not found")
label = Draft.make_label("{text}", FreeCAD.Vector({px}, {py}, {pz}))
label.Target = [target, []]
label.Label = "{label_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created label: {label_name}")
    finally:
        backend.disconnect()


_VIEW_DIRECTIONS: dict[str, tuple[float, float, float]] = {
    "front": (0.0, -1.0, 0.0),
    "back": (0.0, 1.0, 0.0),
    "top": (0.0, 0.0, -1.0),
    "bottom": (0.0, 0.0, 1.0),
    "side": (1.0, 0.0, 0.0),
    "right": (1.0, 0.0, 0.0),
    "left": (-1.0, 0.0, 0.0),
}


def _layout_views(view_names: list[str], page_w: float, page_h: float,
                  scale: float) -> list[tuple[str, tuple[float, float, float], float, float]]:
    """根据视图数量和图幅自动计算视图位置。"""
    margin = 40.0
    available_w = page_w - 2 * margin
    available_h = page_h - 120.0  # 留出标题栏和顶部空间

    if len(view_names) == 1:
        name = view_names[0]
        direction = _VIEW_DIRECTIONS.get(name, _VIEW_DIRECTIONS["front"])
        x = margin + available_w / 2 - 50
        y = margin + available_h / 2
        return [(name, direction, x, y)]

    if len(view_names) == 2:
        positions = [
            (margin + available_w * 0.25, margin + available_h * 0.5),
            (margin + available_w * 0.75, margin + available_h * 0.5),
        ]
        result = []
        for i, name in enumerate(view_names):
            direction = _VIEW_DIRECTIONS.get(name, _VIEW_DIRECTIONS["front"])
            result.append((name, direction, positions[i][0], positions[i][1]))
        return result

    # 默认 3 视图布局：front 左上，top 左下，side 右上
    positions = [
        (margin + available_w * 0.25, margin + available_h * 0.65),
        (margin + available_w * 0.25, margin + available_h * 0.25),
        (margin + available_w * 0.75, margin + available_h * 0.65),
    ]
    result = []
    for i, name in enumerate(view_names[:3]):
        direction = _VIEW_DIRECTIONS.get(name, _VIEW_DIRECTIONS["front"])
        result.append((name, direction, positions[i][0], positions[i][1]))
    return result


def _load_shape_data(input_path: str) -> Any:
    """从输入文件加载 ShapeData。

    支持 .json（本地）以及 .FCStd/.step/.stp（通过 FreeCAD backend）。
    """
    from fc_core.drawing import ShapeData

    path = Path(input_path)
    ext = path.suffix.lower()

    if ext == ".json":
        return ShapeData.load_json(str(path))

    if ext in {".fcstd", ".step", ".stp"}:
        backend = _get_backend()
        backend.connect()
        try:
            code = f"""\
import FreeCAD
import Part

path = r"{path.resolve()}"
ext = path.lower().split(".")[-1]

if ext in ("step", "stp"):
    shape = Part.Shape()
    shape.read(path)
else:
    doc = FreeCAD.open(path)
    shape = None
    for obj in doc.Objects:
        if hasattr(obj, "Shape") and obj.Shape and obj.Shape.Volume > 0:
            shape = obj.Shape
            break
    if shape is None:
        raise ValueError(f"No shape found in {{path}}")

vertices = []
seen_vertices = set()
for v in shape.Vertexes:
    key = (round(v.Point.x, 6), round(v.Point.y, 6), round(v.Point.z, 6))
    if key not in seen_vertices:
        seen_vertices.add(key)
        vertices.append({{"x": v.Point.x, "y": v.Point.y, "z": v.Point.z}})

edges = []
for edge in shape.Edges:
    p1 = edge.Vertexes[0].Point
    p2 = edge.Vertexes[-1].Point
    edges.append({{
        "p1": {{"x": p1.x, "y": p1.y, "z": p1.z}},
        "p2": {{"x": p2.x, "y": p2.y, "z": p2.z}}
    }})

bb = shape.BoundBox
_fc_result = {{
    "status": "ok",
    "data": {{
        "shape": {{
            "vertices": vertices,
            "edges": edges,
            "bound_box": {{
                "x_min": bb.XMin, "y_min": bb.YMin, "z_min": bb.ZMin,
                "x_max": bb.XMax, "y_max": bb.YMax, "z_max": bb.ZMax
            }}
        }}
    }}
}}
"""
            r = backend.execute_code(code)
            if r.status != "ok":
                raise RuntimeError(r.message or "Failed to load shape from FreeCAD")
            shape_dict = r.data.get("shape", {})
            if not shape_dict:
                shape_dict = r.data.get("data", {}).get("shape", {})
            return ShapeData.from_dict(shape_dict)
        finally:
            backend.disconnect()

    raise ValueError(f"Unsupported input format: {ext}")


@draft_group.command("svg")
@click.option("--input", "-i", required=True, help="Input file: .json, .FCStd, .step/.stp")
@click.option("--output", "-o", required=True, help="Output SVG file path.")
@click.option("--page", "-p", default="A3", type=click.Choice(["A4", "A3", "A2", "A1", "A0"]),
              help="Page size.")
@click.option("--scale", "-s", default=0.4, type=float, help="View scale.")
@click.option("--views", default="front,top,side",
              help="Comma-separated view names: front,top,side,back,bottom,left,right.")
@click.option("--title", help="Drawing title.")
@click.option("--unit", help="Organization unit.")
@click.option("--material", help="Material.")
@click.option("--weight", help="Weight.")
@click.option("--drawing-no", help="Drawing number.")
@click.option("--version", help="Drawing version.")
@click.option("--date", help="Date string.")
@click.option("--quantity", help="Quantity.")
@click.option("--drawn-by", default="AI", help="Designer.")
@click.option("--checked-by", help="Checker.")
@_handle_error
def draft_svg(input: str, output: str, page: str, scale: float, views: str,
              title: str | None, unit: str | None, material: str | None,
              weight: str | None, drawing_no: str | None, version: str | None,
              date: str | None, quantity: str | None, drawn_by: str,
              checked_by: str | None) -> None:
    """Generate an engineering drawing SVG from a shape file."""
    from fc_core.drawing import EngineeringDrawingSVG

    from fc_cli.main import _output

    shape_data = _load_shape_data(input)
    drawing = EngineeringDrawingSVG(shape_data, scale=scale, page_size=page, title=title)

    view_names = [v.strip().lower() for v in views.split(",") if v.strip()]
    page_w, page_h = drawing.page_size
    for name, direction, x, y in _layout_views(view_names, page_w, page_h, scale):
        drawing.add_view(name, direction=direction, x=x, y=y)

    drawing.add_title_block(
        title=title or "",
        scale=str(scale),
        material=material or "",
        weight=weight or "",
        unit=unit or "",
        drawing_no=drawing_no or "",
        version=version or "",
        date=date or "",
        quantity=quantity or "",
        drawn_by=drawn_by,
        checked_by=checked_by or "",
    )

    drawing.save(output)
    _output.output({"status": "ok", "output": str(Path(output).resolve())},
                   f"Saved SVG drawing: {output}")
