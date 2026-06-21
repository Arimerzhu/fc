"""Sketch commands.

Commands for 2D sketching:
  sketch new            — Create a new sketch
  sketch add-line       — Add a line
  sketch add-circle     — Add a circle
  sketch add-rect       — Add a rectangle
  sketch add-arc        — Add an arc
  sketch add-ellipse    — Add an ellipse
  sketch add-polygon    — Add a regular polygon
  sketch add-bspline    — Add a B-spline
  sketch add-slot       — Add a slot (obround)
  sketch add-point      — Add a point
  sketch constrain      — Add a constraint
  sketch close          — Close/finalize a sketch
  sketch list           — List all sketches
  sketch get            — Get sketch details
  sketch validate       — Validate a sketch
  sketch solve-status   — Show constraint solving status
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


@click.group("sketch")
def sketch_group():
    """2D sketch commands."""
    pass


@sketch_group.command("new")
@click.option("--name", "-n", help="Sketch name.")
@click.option("--plane", default="XY", type=click.Choice(["XY", "XZ", "YZ"]),
              help="Sketch plane.")
@click.option("--offset", default=0.0, type=float, help="Plane offset.")
@_handle_error
def sketch_new(name: str | None, plane: str, offset: float) -> None:
    """Create a new sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.sketch_new(plane, offset, name or "Sketch")
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@sketch_group.command("add-line")
@click.argument("sketch_name")
@click.option("--start", "-s", default="0,0", help="Start point x,y.")
@click.option("--end", "-e", default="10,0", help="End point x,y.")
@_handle_error
def sketch_add_line(sketch_name: str, start: str, end: str) -> None:
    """Add a line to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        sx, sy = [float(x) for x in start.split(",")]
        ex, ey = [float(x) for x in end.split(",")]
        code = f"""\
import FreeCAD
import Sketcher
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addGeometry(Part.LineSegment(FreeCAD.Vector({sx}, {sy}, 0), FreeCAD.Vector({ex}, {ey}, 0)), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added line to {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("add-circle")
@click.argument("sketch_name")
@click.option("--center", "-c", default="0,0", help="Center x,y.")
@click.option("--radius", "-r", default=5.0, type=float, help="Radius.")
@_handle_error
def sketch_add_circle(sketch_name: str, center: str, radius: float) -> None:
    """Add a circle to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy = [float(x) for x in center.split(",")]
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addGeometry(Part.Circle(FreeCAD.Vector({cx}, {cy}, 0), FreeCAD.Vector(0, 0, 1), {radius}), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added circle to {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("add-rect")
@click.argument("sketch_name")
@click.option("--corner", "-c", default="0,0", help="Corner x,y.")
@click.option("--width", "-w", default=10.0, type=float, help="Width.")
@click.option("--height", "-h", default=10.0, type=float, help="Height.")
@_handle_error
def sketch_add_rect(sketch_name: str, corner: str, width: float, height: float) -> None:
    """Add a rectangle to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy = [float(x) for x in corner.split(",")]
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
p1 = FreeCAD.Vector({cx}, {cy}, 0)
p2 = FreeCAD.Vector({cx + width}, {cy}, 0)
p3 = FreeCAD.Vector({cx + width}, {cy + height}, 0)
p4 = FreeCAD.Vector({cx}, {cy + height}, 0)
sketch.addGeometry(Part.LineSegment(p1, p2), False)
sketch.addGeometry(Part.LineSegment(p2, p3), False)
sketch.addGeometry(Part.LineSegment(p3, p4), False)
sketch.addGeometry(Part.LineSegment(p4, p1), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added rectangle to {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("add-arc")
@click.argument("sketch_name")
@click.option("--center", "-c", default="0,0", help="Center x,y.")
@click.option("--radius", "-r", default=5.0, type=float, help="Radius.")
@click.option("--start-angle", default=0.0, type=float, help="Start angle (deg).")
@click.option("--end-angle", default=90.0, type=float, help="End angle (deg).")
@_handle_error
def sketch_add_arc(sketch_name: str, center: str, radius: float,
                   start_angle: float, end_angle: float) -> None:
    """Add an arc to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy = [float(x) for x in center.split(",")]
        code = f"""\
import FreeCAD
import Part
import math
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
center = FreeCAD.Vector({cx}, {cy}, 0)
start_rad = math.radians({start_angle})
end_rad = math.radians({end_angle})
p1 = center + FreeCAD.Vector({radius} * math.cos(start_rad), {radius} * math.sin(start_rad), 0)
p2 = center + FreeCAD.Vector({radius} * math.cos(end_rad), {radius} * math.sin(end_rad), 0)
sketch.addGeometry(Part.ArcOfCircle(Part.Circle(center, FreeCAD.Vector(0, 0, 1), {radius}), {start_rad}, {end_rad}), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added arc to {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("constrain")
@click.argument("sketch_name")
@click.argument("constraint_type")
@click.option("--elements", "-e", required=True, help="Element indices (comma-sep).")
@click.option("--value", "-v", type=float, help="Constraint value.")
@_handle_error
def sketch_constrain(sketch_name: str, constraint_type: str,
                     elements: str, value: float | None) -> None:
    """Add a constraint to a sketch.

    Constraint types: coincident, horizontal, vertical, parallel, perpendicular,
    equal, fixed, distance, angle, radius, tangent, symmetric, diameter,
    point_on_object, distance_x, distance_y
    """
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        elems = [int(x.strip()) for x in elements.split(",")]
        # Build constraint code based on type
        constraint_map = {
            "horizontal": "Sketcher.Constraint('Horizontal', {})",
            "vertical": "Sketcher.Constraint('Vertical', {})",
            "coincident": "Sketcher.Constraint('Coincident', {}, {})",
            "parallel": "Sketcher.Constraint('Parallel', {}, {})",
            "perpendicular": "Sketcher.Constraint('Perpendicular', {}, {})",
            "equal": "Sketcher.Constraint('Equal', {}, {})",
            "fixed": "Sketcher.Constraint('Fixed', {})",
            "distance": "Sketcher.Constraint('Distance', {}, {}, {})",
            "angle": "Sketcher.Constraint('Angle', {}, {}, {})",
            "radius": "Sketcher.Constraint('Radius', {}, {})",
            "diameter": "Sketcher.Constraint('Diameter', {}, {})",
            "tangent": "Sketcher.Constraint('Tangent', {}, {})",
            "symmetric": "Sketcher.Constraint('Symmetric', {}, {}, {})",
            "point_on_object": "Sketcher.Constraint('PointOnObject', {}, {})",
            "distance_x": "Sketcher.Constraint('DistanceX', {}, {}, {})",
            "distance_y": "Sketcher.Constraint('DistanceY', {}, {}, {})",
        }

        if len(elems) == 1:
            elem_str = str(elems[0])
        elif len(elems) == 2:
            elem_str = f"{elems[0]}, {elems[1]}"
        else:
            elem_str = ", ".join(str(e) for e in elems)

        if constraint_type in ("horizontal", "vertical", "fixed"):
            constraint_code = f"Sketcher.Constraint('{constraint_type.capitalize()}', {elem_str})"
        elif value is not None and constraint_type in ("distance", "angle", "radius", "diameter", "distance_x", "distance_y"):
            constraint_code = f"Sketcher.Constraint('{constraint_type.capitalize()}', {elem_str}, {value})"
        elif constraint_type in constraint_map:
            if "{}" in constraint_map[constraint_type]:
                count = constraint_map[constraint_type].count("{}")
                if count == 1:
                    constraint_code = constraint_map[constraint_type].format(elem_str)
                elif count == 2:
                    constraint_code = constraint_map[constraint_type].format(elems[0], elems[1])
                else:
                    constraint_code = constraint_map[constraint_type].format(elems[0], elems[1], value or 0)
            else:
                constraint_code = f"Sketcher.Constraint('{constraint_type.capitalize()}', {elem_str})"
        else:
            constraint_code = f"Sketcher.Constraint('{constraint_type}', {elem_str})"

        code = f"""\
import FreeCAD
import Sketcher
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addConstraint({constraint_code})
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added {constraint_type} constraint to {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("close")
@click.argument("sketch_name")
@_handle_error
def sketch_close(sketch_name: str) -> None:
    """Close/finalize a sketch (recompute to validate)."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Sketch '{sketch_name}' closed")
    finally:
        backend.disconnect()


@sketch_group.command("list")
@_handle_error
def sketch_list() -> None:
    """List all sketches."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = """\
import FreeCAD
doc = FreeCAD.ActiveDocument
sketches = [obj for obj in doc.Objects if obj.TypeId == "Sketcher::SketchObject"]
_fc_result = {
    "status": "ok",
    "data": {"sketches": [{"name": s.Name, "label": s.Label} for s in sketches], "count": len(sketches)},
    "message": ""
}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"{r.data.get('data', {}).get('count', 0)} sketch(es):")
    finally:
        backend.disconnect()


@sketch_group.command("get")
@click.argument("name")
@_handle_error
def sketch_get(name: str) -> None:
    """Get sketch details."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{name}")
if sketch is None:
    raise ValueError(f"Sketch '{name}' not found")
geo_count = sketch.GeometryCount
constraints = sketch.Constraints
constraint_info = []
if constraints:
    for c in constraints:
        constraint_info.append({{"type": c.Type, "value": c.Value if hasattr(c, "Value") else None}})
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": sketch.Name,
        "label": sketch.Label,
        "geometry_count": geo_count,
        "constraint_count": len(constraints) if constraints else 0,
        "constraints": constraint_info,
        "fully_constrained": sketch.FullyConstrained if hasattr(sketch, "FullyConstrained") else None,
    }},
    "message": ""
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"Sketch '{name}':")
    finally:
        backend.disconnect()


@sketch_group.command("validate")
@click.argument("name")
@_handle_error
def sketch_validate(name: str) -> None:
    """Validate a sketch for errors."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{name}")
if sketch is None:
    raise ValueError(f"Sketch '{name}' not found")
# Check for open wires, over-constraints, etc.
issues = []
if hasattr(sketch, "validate"):
    try:
        sketch.validate()
    except Exception as e:
        issues.append(str(e))
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": sketch.Name,
        "valid": len(issues) == 0,
        "issues": issues,
        "geometry_count": sketch.GeometryCount,
        "constraint_count": len(sketch.Constraints) if sketch.Constraints else 0,
    }},
    "message": "Valid" if not issues else f"{{len(issues)}} issue(s) found"
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Validation: {name}")
    finally:
        backend.disconnect()


@sketch_group.command("solve-status")
@click.argument("name")
@_handle_error
def sketch_solve_status(name: str) -> None:
    """Show constraint solving status of a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{name}")
if sketch is None:
    raise ValueError(f"Sketch '{name}' not found")
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": sketch.Name,
        "solver_status": str(sketch.Solver) if hasattr(sketch, "Solver") else "unknown",
        "fully_constrained": sketch.FullyConstrained if hasattr(sketch, "FullyConstrained") else None,
        "geometry_count": sketch.GeometryCount,
        "constraint_count": len(sketch.Constraints) if sketch.Constraints else 0,
        "degrees_of_freedom": sketch.DOF if hasattr(sketch, "DOF") else None,
    }},
    "message": ""
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"Solve status for '{name}':")
    finally:
        backend.disconnect()


@sketch_group.command("add-ellipse")
@click.argument("sketch_name")
@click.option("--center", "-c", default="0,0", help="Center x,y.")
@click.option("--major-radius", default=10.0, type=float, help="Major radius.")
@click.option("--minor-radius", default=5.0, type=float, help="Minor radius.")
@click.option("--major-angle", default=0.0, type=float, help="Major axis angle (deg).")
@_handle_error
def sketch_add_ellipse(sketch_name: str, center: str, major_radius: float,
                       minor_radius: float, major_angle: float) -> None:
    """Add an ellipse to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy = [float(x) for x in center.split(",")]
        code = f"""\
import FreeCAD
import Part
import math
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
center = FreeCAD.Vector({cx}, {cy}, 0)
ellipse = Part.Ellipse(center, {major_radius}, {minor_radius})
if {major_angle} != 0:
    ellipse.rotate(FreeCAD.Placement(center, FreeCAD.Rotation(0, 0, {major_angle})))
sketch.addGeometry(ellipse.toBSpline(), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added ellipse to {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("add-polygon")
@click.argument("sketch_name")
@click.option("--center", "-c", default="0,0", help="Center x,y.")
@click.option("--radius", "-r", default=5.0, type=float, help="Circumradius.")
@click.option("--sides", "-s", default=6, type=int, help="Number of sides.")
@_handle_error
def sketch_add_polygon(sketch_name: str, center: str, radius: float,
                       sides: int) -> None:
    """Add a regular polygon to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy = [float(x) for x in center.split(",")]
        code = f"""\
import FreeCAD
import Part
import math
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
center = FreeCAD.Vector({cx}, {cy}, 0)
points = []
for i in range({sides}):
    angle = 2 * math.pi * i / {sides}
    x = {cx} + {radius} * math.cos(angle)
    y = {cy} + {radius} * math.sin(angle)
    points.append(FreeCAD.Vector(x, y, 0))
points.append(points[0])
for i in range(len(points) - 1):
    sketch.addGeometry(Part.LineSegment(points[i], points[i+1]), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added {sides}-gon to {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("add-bspline")
@click.argument("sketch_name")
@click.option("--points", "-p", required=True,
              help="Control points as semicolon-separated x,y pairs.")
@click.option("--closed", is_flag=True, default=False, help="Close the B-spline.")
@_handle_error
def sketch_add_bspline(sketch_name: str, points: str, closed: bool) -> None:
    """Add a B-spline curve to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        pts = []
        for pt_str in points.split(";"):
            pt_str = pt_str.strip()
            if pt_str:
                coords = [float(x) for x in pt_str.split(",")]
                pts.append(f"FreeCAD.Vector({coords[0]}, {coords[1]}, 0)")
        points_list = ", ".join(pts)
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
pts = [{points_list}]
if len(pts) < 2:
    raise ValueError("At least 2 control points required")
bspline = Part.BSplineCurve()
bspline.interpolate(pts, {str(closed).lower()})
sketch.addGeometry(bspline.toBSpline(), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added B-spline to {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("add-slot")
@click.argument("sketch_name")
@click.option("--center", "-c", default="0,0", help="Center x,y.")
@click.option("--length", "-l", default=20.0, type=float, help="Slot length.")
@click.option("--width", "-w", default=5.0, type=float, help="Slot width (diameter).")
@click.option("--angle", default=0.0, type=float, help="Rotation angle (deg).")
@_handle_error
def sketch_add_slot(sketch_name: str, center: str, length: float,
                    width: float, angle: float) -> None:
    """Add a slot (obround) to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy = [float(x) for x in center.split(",")]
        code = f"""\
import FreeCAD
import Part
import math
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
center = FreeCAD.Vector({cx}, {cy}, 0)
half_len = {length} / 2
radius = {width} / 2
angle_rad = math.radians({angle})
dx = half_len * math.cos(angle_rad)
dy = half_len * math.sin(angle_rad)
p1 = FreeCAD.Vector({cx} - dx, {cy} - dy, 0)
p2 = FreeCAD.Vector({cx} + dx, {cy} + dy, 0)
sketch.addGeometry(Part.ArcOfCircle(Part.Circle(p1, FreeCAD.Vector(0,0,1), radius), math.pi/2 - angle_rad, 3*math.pi/2 - angle_rad), False)
sketch.addGeometry(Part.ArcOfCircle(Part.Circle(p2, FreeCAD.Vector(0,0,1), radius), -math.pi/2 - angle_rad, math.pi/2 - angle_rad), False)
sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(p1.x - radius*math.sin(angle_rad), p1.y + radius*math.cos(angle_rad), 0), FreeCAD.Vector(p2.x - radius*math.sin(angle_rad), p2.y + radius*math.cos(angle_rad), 0)), False)
sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(p1.x + radius*math.sin(angle_rad), p1.y - radius*math.cos(angle_rad), 0), FreeCAD.Vector(p2.x + radius*math.sin(angle_rad), p2.y - radius*math.cos(angle_rad), 0)), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added slot to {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("add-point")
@click.argument("sketch_name")
@click.option("--position", "-p", default="0,0", help="Position x,y.")
@_handle_error
def sketch_add_point(sketch_name: str, position: str) -> None:
    """Add a point to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py = [float(x) for x in position.split(",")]
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addGeometry(Part.Point(FreeCAD.Vector({px}, {py}, 0)), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added point to {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("delete-geom")
@click.argument("sketch_name")
@click.argument("indices")
@_handle_error
def sketch_delete_geom(sketch_name: str, indices: str) -> None:
    """Delete geometry elements from a sketch by index."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        idx_list = [int(x.strip()) for x in indices.split(",")]
        idx_list_sorted = sorted(idx_list, reverse=True)
        deletions = "\n".join([f"sketch.delGeometry({i})" for i in idx_list_sorted])
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
{deletions}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Deleted {len(idx_list)} geometry element(s) from {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("trim")
@click.argument("sketch_name")
@click.argument("geom_index")
@click.option("--point", "-p", help="Trim point as x,y.")
@_handle_error
def sketch_trim(sketch_name: str, geom_index: int, point: str | None) -> None:
    """Trim a geometry element at a point."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py = [float(x) for x in point.split(",")] if point else (0, 0)
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
geom = sketch.Geometry[{geom_index}]
if geom is None:
    raise ValueError(f"Geometry index {geom_index} not found")
trim_point = FreeCAD.Vector({px}, {py}, 0)
sketch.trim({geom_index}, trim_point)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Trimmed geometry {geom_index} in {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("mirror")
@click.argument("sketch_name")
@click.option("--elements", "-e", required=True, help="Element indices (comma-sep).")
@click.option("--axis", default="x", type=click.Choice(["x", "y"]),
              help="Mirror axis within the sketch plane.")
@_handle_error
def sketch_mirror(sketch_name: str, elements: str, axis: str) -> None:
    """Mirror sketch geometry elements."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        elems = [int(x.strip()) for x in elements.split(",")]
        elem_str = ", ".join(str(e) for e in elems)
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
for idx in [{elem_str}]:
    if idx >= sketch.GeometryCount:
        raise ValueError(f"Geometry index {idx} out of range")
    geom = sketch.Geometry[idx]
    if hasattr(geom, "mirror"):
        if "{axis}" == "x":
            geom.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0))
        else:
            geom.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0))
        sketch.addGeometry(geom, False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Mirrored {len(elems)} element(s) in {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("clone")
@click.argument("sketch_name")
@click.option("--elements", "-e", required=True, help="Element indices (comma-sep).")
@click.option("--offset", default="10,0", help="Clone offset as dx,dy.")
@_handle_error
def sketch_clone(sketch_name: str, elements: str, offset: str) -> None:
    """Clone sketch geometry elements with an offset."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        elems = [int(x.strip()) for x in elements.split(",")]
        dx, dy = [float(x) for x in offset.split(",")]
        elem_str = ", ".join(str(e) for e in elems)
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
offset = FreeCAD.Vector({dx}, {dy}, 0)
for idx in [{elem_str}]:
    if idx >= sketch.GeometryCount:
        raise ValueError(f"Geometry index {idx} out of range")
    geom = sketch.Geometry[idx]
    if hasattr(geom, "copy"):
        new_geom = geom.copy()
        if hasattr(new_geom, "move"):
            new_geom.move(offset)
        sketch.addGeometry(new_geom, False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Cloned {len(elems)} element(s) in {sketch_name}")
    finally:
        backend.disconnect()


@sketch_group.command("export")
@click.argument("sketch_name")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output DXF file path.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def sketch_export(sketch_name: str, output: str, overwrite: bool) -> None:
    """Export a sketch to DXF format."""
    import os
    from fc_cli.main import _output
    if os.path.exists(output) and not overwrite:
        _output.error(f"File exists: {output}", code="FILE_EXISTS",
                      suggestion="Use --overwrite to replace")
        return
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import importDXF
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
importDXF.export([sketch], r"{os.path.abspath(output)}")
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Exported {sketch_name} to {output}")
    finally:
        backend.disconnect()
