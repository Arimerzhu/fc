"""Query MCP tools: get objects, get properties, list objects."""

from __future__ import annotations

from fc_core.types import ToolResponse
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
def list_objects(backend: str = "headless") -> dict:
    """List all objects in the current document.

    Args:
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.object_list()
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def get_object(obj_name: str, backend: str = "headless") -> dict:
    """Get detailed information about an object.

    Args:
        obj_name: Name of the object
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.object_get(obj_name)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def get_object_properties(obj_name: str, backend: str = "headless") -> dict:
    """Get all properties of an object.

    Args:
        obj_name: Name of the object
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{obj_name}")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
props = {{}}
for prop in obj.PropertiesList:
    try:
        val = getattr(obj, prop)
        if isinstance(val, (int, float, str, bool)):
            props[prop] = val
    except Exception:
        pass
_fc_result = {{"status": "ok", "data": {{"name": obj.Name, "properties": props}}, "message": ""}}
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def get_bounding_box(obj_name: str, backend: str = "headless") -> dict:
    """Get the bounding box of an object.

    Args:
        obj_name: Name of the object
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{obj_name}")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
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
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def get_shape_info(obj_name: str, backend: str = "headless") -> dict:
    """Get shape information (volume, area, center of mass, etc.) of an object.

    Args:
        obj_name: Name of the object
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{obj_name}")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
if hasattr(obj, "Shape") and obj.Shape:
    shape = obj.Shape
    _fc_result = {{
        "status": "ok",
        "data": {{
            "volume": shape.Volume,
            "area": shape.Area,
            "length": shape.Length,
            "center_of_mass": list(shape.CenterOfMass),
            "solid_count": len(shape.Solids),
            "face_count": len(shape.Faces),
            "edge_count": len(shape.Edges),
            "vertex_count": len(shape.Vertexes),
            "is_valid": shape.isValid(),
            "is_closed": shape.isClosed() if hasattr(shape, "isClosed") else None,
        }},
        "message": ""
    }}
else:
    _fc_result = {{"status": "error", "data": {{}}, "message": "Object has no Shape"}}
"""
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def get_version(backend: str = "headless") -> dict:
    """Get the FreeCAD version.

    Args:
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        version = be.get_version()
        return ToolResponse.ok("get_version", {"version": version}, f"FreeCAD {version}").to_dict()
    finally:
        be.disconnect()
