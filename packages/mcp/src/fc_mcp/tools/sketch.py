"""Sketch MCP tools: create sketch, add geometry, add constraints."""

from __future__ import annotations

from fc_mcp.server import mcp


def _get_backend(backend_type: str = "headless", freecad_path: str | None = None,
                 host: str = "localhost", port: int = 9875):
    if backend_type == "rpc":
        from fc_core.backend import RPCBackend
        return RPCBackend(host=host, port=port)
    else:
        from fc_core.backend import HeadlessBackend
        return HeadlessBackend(freecad_path=freecad_path)


@mcp.tool()
def sketch_new(
    name: str = "Sketch",
    plane: str = "XY",
    offset: float = 0.0,
    backend: str = "headless",
) -> dict:
    """Create a new sketch.

    Args:
        name: Sketch name
        plane: Sketch plane ('XY', 'XZ', or 'YZ')
        offset: Plane offset from origin
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.sketch_new(plane, offset, name)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def sketch_add_line(
    sketch_name: str,
    start_x: float = 0.0,
    start_y: float = 0.0,
    end_x: float = 10.0,
    end_y: float = 0.0,
    backend: str = "headless",
) -> dict:
    """Add a line to a sketch.

    Args:
        sketch_name: Name of the sketch
        start_x: Start X coordinate
        start_y: Start Y coordinate
        end_x: End X coordinate
        end_y: End Y coordinate
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addGeometry(Part.LineSegment(FreeCAD.Vector({start_x}, {start_y}, 0), FreeCAD.Vector({end_x}, {end_y}, 0)), False)
doc.recompute()
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def sketch_add_circle(
    sketch_name: str,
    center_x: float = 0.0,
    center_y: float = 0.0,
    radius: float = 5.0,
    backend: str = "headless",
) -> dict:
    """Add a circle to a sketch.

    Args:
        sketch_name: Name of the sketch
        center_x: Center X coordinate
        center_y: Center Y coordinate
        radius: Circle radius
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addGeometry(Part.Circle(FreeCAD.Vector({center_x}, {center_y}, 0), FreeCAD.Vector(0, 0, 1), {radius}), False)
doc.recompute()
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def sketch_add_rect(
    sketch_name: str,
    corner_x: float = 0.0,
    corner_y: float = 0.0,
    width: float = 10.0,
    height: float = 10.0,
    backend: str = "headless",
) -> dict:
    """Add a rectangle to a sketch.

    Args:
        sketch_name: Name of the sketch
        corner_x: Corner X coordinate
        corner_y: Corner Y coordinate
        width: Rectangle width
        height: Rectangle height
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
p1 = FreeCAD.Vector({corner_x}, {corner_y}, 0)
p2 = FreeCAD.Vector({corner_x + width}, {corner_y}, 0)
p3 = FreeCAD.Vector({corner_x + width}, {corner_y + height}, 0)
p4 = FreeCAD.Vector({corner_x}, {corner_y + height}, 0)
sketch.addGeometry(Part.LineSegment(p1, p2), False)
sketch.addGeometry(Part.LineSegment(p2, p3), False)
sketch.addGeometry(Part.LineSegment(p3, p4), False)
sketch.addGeometry(Part.LineSegment(p4, p1), False)
doc.recompute()
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def sketch_add_arc(
    sketch_name: str,
    center_x: float = 0.0,
    center_y: float = 0.0,
    radius: float = 5.0,
    start_angle: float = 0.0,
    end_angle: float = 90.0,
    backend: str = "headless",
) -> dict:
    """Add an arc to a sketch.

    Args:
        sketch_name: Name of the sketch
        center_x: Center X coordinate
        center_y: Center Y coordinate
        radius: Arc radius
        start_angle: Start angle in degrees
        end_angle: End angle in degrees
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
import Part
import math
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
center = FreeCAD.Vector({center_x}, {center_y}, 0)
start_rad = math.radians({start_angle})
end_rad = math.radians({end_angle})
sketch.addGeometry(Part.ArcOfCircle(Part.Circle(center, FreeCAD.Vector(0, 0, 1), {radius}), start_rad, end_rad), False)
doc.recompute()
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def sketch_add_polygon(
    sketch_name: str,
    center_x: float = 0.0,
    center_y: float = 0.0,
    radius: float = 5.0,
    sides: int = 6,
    backend: str = "headless",
) -> dict:
    """Add a regular polygon to a sketch.

    Args:
        sketch_name: Name of the sketch
        center_x: Center X coordinate
        center_y: Center Y coordinate
        radius: Circumradius
        sides: Number of sides
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
import Part
import math
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
center = FreeCAD.Vector({center_x}, {center_y}, 0)
points = []
for i in range({sides}):
    angle = 2 * math.pi * i / {sides}
    points.append(center + FreeCAD.Vector({radius} * math.cos(angle), {radius} * math.sin(angle), 0))
for i in range({sides}):
    sketch.addGeometry(Part.LineSegment(points[i], points[(i + 1) % {sides}]), False)
doc.recompute()
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def sketch_constrain_coincident(
    sketch_name: str,
    vertex1: int,
    vertex2: int,
    backend: str = "headless",
) -> dict:
    """Add a coincident constraint between two vertices.

    Args:
        sketch_name: Name of the sketch
        vertex1: First geometry index
        vertex2: Second geometry index
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
import Sketcher
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addConstraint(Sketcher.Constraint('Coincident', {vertex1}, {vertex2}))
doc.recompute()
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def sketch_constrain_horizontal(
    sketch_name: str,
    edge_index: int,
    backend: str = "headless",
) -> dict:
    """Add a horizontal constraint to an edge.

    Args:
        sketch_name: Name of the sketch
        edge_index: Geometry index of the edge
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
import Sketcher
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addConstraint(Sketcher.Constraint('Horizontal', {edge_index}))
doc.recompute()
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def sketch_constrain_vertical(
    sketch_name: str,
    edge_index: int,
    backend: str = "headless",
) -> dict:
    """Add a vertical constraint to an edge.

    Args:
        sketch_name: Name of the sketch
        edge_index: Geometry index of the edge
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
import Sketcher
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addConstraint(Sketcher.Constraint('Vertical', {edge_index}))
doc.recompute()
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def sketch_constrain_distance(
    sketch_name: str,
    element1: int,
    element2: int,
    value: float,
    backend: str = "headless",
) -> dict:
    """Add a distance constraint between two elements.

    Args:
        sketch_name: Name of the sketch
        element1: First geometry index
        element2: Second geometry index
        value: Distance value in mm
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
import Sketcher
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addConstraint(Sketcher.Constraint('Distance', {element1}, {element2}, {value}))
doc.recompute()
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def sketch_constrain_radius(
    sketch_name: str,
    arc_index: int,
    radius: float,
    backend: str = "headless",
) -> dict:
    """Add a radius constraint to an arc or circle.

    Args:
        sketch_name: Name of the sketch
        arc_index: Geometry index of the arc/circle
        radius: Radius value in mm
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
import Sketcher
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addConstraint(Sketcher.Constraint('Radius', {arc_index}, {radius}))
doc.recompute()
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def sketch_get_info(sketch_name: str, backend: str = "headless") -> dict:
    """Get information about a sketch.

    Args:
        sketch_name: Name of the sketch
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": sketch.Name,
        "label": sketch.Label,
        "geometry_count": sketch.GeometryCount,
        "constraint_count": len(sketch.Constraints) if sketch.Constraints else 0,
        "fully_constrained": sketch.FullyConstrained if hasattr(sketch, "FullyConstrained") else None,
    }},
    "message": ""
}}
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()
