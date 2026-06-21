"""Geometry MCP tools: create primitives, edit, delete, boolean operations."""

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
def geometry_create_box(
    name: str = "Box",
    length: float = 10.0,
    width: float = 10.0,
    height: float = 10.0,
    pos_x: float = 0.0,
    pos_y: float = 0.0,
    pos_z: float = 0.0,
    backend: str = "headless",
) -> dict:
    """Create a box (rectangular prism) primitive.

    Args:
        name: Object name
        length: Length in mm
        width: Width in mm
        height: Height in mm
        pos_x: X position
        pos_y: Y position
        pos_z: Z position
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        from fc_core.types import Vec3
        from fc_core.geometry import PrimitivesMixin

        class _Helper(PrimitivesMixin):
            _backend = be

        h = _Helper()
        r = h.add_box(name=name, length=length, width=width, height=height,
                      position=Vec3(pos_x, pos_y, pos_z))
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_create_cylinder(
    name: str = "Cylinder",
    radius: float = 5.0,
    height: float = 10.0,
    pos_x: float = 0.0,
    pos_y: float = 0.0,
    pos_z: float = 0.0,
    backend: str = "headless",
) -> dict:
    """Create a cylinder primitive.

    Args:
        name: Object name
        radius: Radius in mm
        height: Height in mm
        pos_x: X position
        pos_y: Y position
        pos_z: Z position
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        from fc_core.types import Vec3
        from fc_core.geometry import PrimitivesMixin

        class _Helper(PrimitivesMixin):
            _backend = be

        h = _Helper()
        r = h.add_cylinder(name=name, radius=radius, height=height,
                           position=Vec3(pos_x, pos_y, pos_z))
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_create_sphere(
    name: str = "Sphere",
    radius: float = 5.0,
    pos_x: float = 0.0,
    pos_y: float = 0.0,
    pos_z: float = 0.0,
    backend: str = "headless",
) -> dict:
    """Create a sphere primitive.

    Args:
        name: Object name
        radius: Radius in mm
        pos_x: X position
        pos_y: Y position
        pos_z: Z position
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        from fc_core.types import Vec3
        from fc_core.geometry import PrimitivesMixin

        class _Helper(PrimitivesMixin):
            _backend = be

        h = _Helper()
        r = h.add_sphere(name=name, radius=radius,
                         position=Vec3(pos_x, pos_y, pos_z))
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_create_cone(
    name: str = "Cone",
    radius1: float = 5.0,
    radius2: float = 0.0,
    height: float = 10.0,
    backend: str = "headless",
) -> dict:
    """Create a cone primitive.

    Args:
        name: Object name
        radius1: Bottom radius in mm
        radius2: Top radius in mm (0 for sharp cone)
        height: Height in mm
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        from fc_core.geometry import PrimitivesMixin

        class _Helper(PrimitivesMixin):
            _backend = be

        h = _Helper()
        r = h.add_cone(name=name, radius1=radius1, radius2=radius2, height=height)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_create_torus(
    name: str = "Torus",
    radius1: float = 10.0,
    radius2: float = 2.0,
    backend: str = "headless",
) -> dict:
    """Create a torus primitive.

    Args:
        name: Object name
        radius1: Main radius (center to tube center)
        radius2: Tube radius
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        from fc_core.geometry import PrimitivesMixin

        class _Helper(PrimitivesMixin):
            _backend = be

        h = _Helper()
        r = h.add_torus(name=name, radius1=radius1, radius2=radius2)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_boolean_union(
    base_name: str,
    tool_name: str,
    result_name: str = "",
    backend: str = "headless",
) -> dict:
    """Perform boolean union (fuse) of two objects.

    Args:
        base_name: Name of the base object
        tool_name: Name of the tool object to fuse
        result_name: Name for the result object
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.boolean_union(base_name, tool_name, result_name)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_boolean_cut(
    base_name: str,
    tool_name: str,
    result_name: str = "",
    backend: str = "headless",
) -> dict:
    """Perform boolean cut (subtraction) of tool from base.

    Args:
        base_name: Name of the base object
        tool_name: Name of the tool object to subtract
        result_name: Name for the result object
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.boolean_cut(base_name, tool_name, result_name)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_boolean_common(
    obj1_name: str,
    obj2_name: str,
    result_name: str = "",
    backend: str = "headless",
) -> dict:
    """Perform boolean common (intersection) of two objects.

    Args:
        obj1_name: Name of the first object
        obj2_name: Name of the second object
        result_name: Name for the result object
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.boolean_common(obj1_name, obj2_name, result_name)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_fillet_edges(
    obj_name: str,
    radius: float = 1.0,
    edges: list[int] | None = None,
    result_name: str = "",
    backend: str = "headless",
) -> dict:
    """Apply fillet to edges of an object.

    Args:
        obj_name: Name of the object
        radius: Fillet radius in mm
        edges: List of edge indices (None for all edges)
        result_name: Name for the result object
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.fillet_edges(obj_name, radius, edges, result_name)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_chamfer_edges(
    obj_name: str,
    size: float = 1.0,
    edges: list[int] | None = None,
    result_name: str = "",
    backend: str = "headless",
) -> dict:
    """Apply chamfer to edges of an object.

    Args:
        obj_name: Name of the object
        size: Chamfer size in mm
        edges: List of edge indices (None for all edges)
        result_name: Name for the result object
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.chamfer_edges(obj_name, size, edges, result_name)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_mirror(
    obj_name: str,
    plane: str = "XY",
    result_name: str = "",
    backend: str = "headless",
) -> dict:
    """Mirror an object across a plane.

    Args:
        obj_name: Name of the object
        plane: Mirror plane ('XY', 'XZ', or 'YZ')
        result_name: Name for the result object
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.mirror_object(obj_name, plane, result_name)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_scale(
    obj_name: str,
    factor: float | list[float] = 1.0,
    result_name: str = "",
    backend: str = "headless",
) -> dict:
    """Scale an object.

    Args:
        obj_name: Name of the object
        factor: Uniform scale factor or [x, y, z] factors
        result_name: Name for the result object
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.scale_object(obj_name, factor, result_name)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_delete(obj_name: str, backend: str = "headless") -> dict:
    """Delete an object from the document.

    Args:
        obj_name: Name of the object to delete
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.object_delete(obj_name)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def geometry_transform(
    obj_name: str,
    pos_x: float | None = None,
    pos_y: float | None = None,
    pos_z: float | None = None,
    rot_x: float | None = None,
    rot_y: float | None = None,
    rot_z: float | None = None,
    backend: str = "headless",
) -> dict:
    """Transform an object's position and/or rotation.

    Args:
        obj_name: Name of the object
        pos_x: New X position
        pos_y: New Y position
        pos_z: New Z position
        rot_x: X rotation in degrees
        rot_y: Y rotation in degrees
        rot_z: Z rotation in degrees
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        position = (pos_x, pos_y, pos_z) if any(v is not None for v in (pos_x, pos_y, pos_z)) else None
        rotation = (rot_x, rot_y, rot_z) if any(v is not None for v in (rot_x, rot_y, rot_z)) else None
        code_lines = [
            'import FreeCAD',
            'doc = FreeCAD.ActiveDocument',
            f'obj = doc.getObject("{obj_name}")',
            'if obj is None:',
            f'    raise ValueError(f"Object \'{obj_name}\' not found")',
        ]
        if position:
            px = pos_x or 0
            py = pos_y or 0
            pz = pos_z or 0
            code_lines.append(f'obj.Placement.Base = FreeCAD.Vector({px}, {py}, {pz})')
        if rotation:
            rx = rot_x or 0
            ry = rot_y or 0
            rz = rot_z or 0
            code_lines.append(f'obj.Placement.Rotation = FreeCAD.Rotation({rx}, {ry}, {rz})')
        code_lines.append('doc.recompute()')
        r = be.execute_code("\n".join(code_lines))
        return r.to_dict()
    finally:
        be.disconnect()
