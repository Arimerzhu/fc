"""Mesh commands.

Commands for mesh operations:
  mesh import       — Import a mesh file
  mesh export       — Export to mesh format
  mesh analyze      — Analyze mesh quality
  mesh repair       — Repair mesh defects
  mesh refine       — Refine mesh tessellation
  mesh decimate     — Reduce mesh polygon count
  mesh boolean      — Boolean operations on meshes
  mesh section      — Create cross-section from mesh
  mesh list         — List all mesh objects
  mesh info         — Get mesh information
"""

from __future__ import annotations

import os

import click


def _handle_error(f):
    from fc_cli.main import handle_error
    return handle_error(f)


def _get_backend():
    """获取 backend 实例（委托给 main.get_backend 统一管理）。"""
    from fc_cli.main import get_backend
    return get_backend()


@click.group("mesh")
def mesh_group():
    """Mesh import, export, analysis, and repair commands."""
    pass


@mesh_group.command("import")
@click.argument("path", type=click.Path(exists=True))
@click.option("--name", "-n", help="Object name for the imported mesh.")
@_handle_error
def mesh_import(path: str, name: str | None) -> None:
    """Import a mesh file (STL, OBJ, PLY, OFF, 3MF)."""
    from fc_cli.main import _output
    abs_path = os.path.abspath(path)
    ext = os.path.splitext(path)[1].lstrip(".").lower()

    backend = _get_backend()
    try:
        backend.connect()
        obj_name = name or os.path.splitext(os.path.basename(path))[0]

        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
mesh = Mesh.Mesh()
mesh.read(r"{abs_path}")
obj = doc.addObject("Mesh::Feature", "{obj_name}")
obj.Mesh = mesh
doc.recompute()
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{obj_name}",
        "file": r"{abs_path}",
        "format": "{ext}",
        "count_points": mesh.CountPoints,
        "count_edges": mesh.CountEdges,
        "count_facets": mesh.CountFacets,
        "is_solid": mesh.isSolid(),
    }},
    "message": "Imported mesh: {obj_name}"
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@mesh_group.command("export")
@click.argument("output", type=click.Path())
@click.option("--format", "-f", "fmt", default="stl",
              type=click.Choice(["stl", "obj", "ply", "off"]),
              help="Export mesh format.")
@click.option("--tolerance", "-t", default=0.1, type=float,
              help="Mesh tessellation tolerance.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def mesh_export(output: str, fmt: str, tolerance: float, overwrite: bool) -> None:
    """Export to mesh format (STL, OBJ, PLY, OFF)."""
    from fc_cli.main import _output
    abs_output = os.path.abspath(output)
    if os.path.exists(abs_output) and not overwrite:
        _output.error(f"File exists: {output}", code="FILE_EXISTS",
                      suggestion="Use --overwrite to replace")
        return

    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
meshes = [obj for obj in doc.Objects if hasattr(obj, "Mesh") and obj.Mesh]
if not meshes:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No mesh objects in document"}}
else:
    # Export all meshes combined, or the first one
    combined = Mesh.Mesh()
    for obj in meshes:
        combined.addMesh(obj.Mesh)
    combined.write(r"{abs_output}")
    _fc_result = {{
        "status": "ok",
        "data": {{"file": r"{abs_output}", "format": "{fmt}", "objects_exported": len(meshes)}},
        "message": "Exported {{len(meshes)}} mesh(es) to {abs_output}"
    }}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@mesh_group.command("analyze")
@click.option("--name", "-n", help="Specific mesh object to analyze.")
@_handle_error
def mesh_analyze(name: str | None) -> None:
    """Analyze mesh quality."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        name_filter = f'"{name}"' if name else "None"

        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
target_name = {name_filter}
meshes = []
for obj in doc.Objects:
    if hasattr(obj, "Mesh") and obj.Mesh:
        if target_name is None or obj.Name == target_name:
            meshes.append(obj)
if not meshes:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No mesh objects found"}}
else:
    results = []
    for obj in meshes:
        m = obj.Mesh
        info = {{
            "name": obj.Name,
            "count_points": m.CountPoints,
            "count_edges": m.CountEdges,
            "count_facets": m.CountFacets,
            "is_solid": m.isSolid(),
            "has_non_manifolds": m.hasNonManifolds() if hasattr(m, "hasNonManifolds") else None,
            "has_self_intersections": m.hasSelfIntersections() if hasattr(m, "hasSelfIntersections") else None,
            "bounding_box": {{
                "x": [m.BoundBox.XMin, m.BoundBox.XMax],
                "y": [m.BoundBox.YMin, m.BoundBox.YMax],
                "z": [m.BoundBox.ZMin, m.BoundBox.ZMax],
            }},
            "surface_area": m.getSurfaceArea() if hasattr(m, "getSurfaceArea") else None,
            "volume": m.getVolume() if hasattr(m, "getVolume") else None,
        }}
        results.append(info)
    _fc_result = {{
        "status": "ok",
        "data": {{"meshes": results, "count": len(results)}},
        "message": "Analyzed {{len(results)}} mesh(es)"
    }}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@mesh_group.command("repair")
@click.option("--name", "-n", help="Specific mesh object to repair.")
@click.option("--fix-degenerates", is_flag=True, help="Remove degenerate facets.")
@click.option("--fix-duplicates", is_flag=True, help="Remove duplicate facets.")
@click.option("--fix-normals", is_flag=True, help="Fix flipped normals.")
@_handle_error
def mesh_repair(name: str | None, fix_degenerates: bool, fix_duplicates: bool,
                fix_normals: bool) -> None:
    """Repair mesh defects."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        name_filter = f'"{name}"' if name else "None"

        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
target_name = {name_filter}
meshes = [obj for obj in doc.Objects if hasattr(obj, "Mesh") and obj.Mesh and (target_name is None or obj.Name == target_name)]
if not meshes:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No mesh objects found"}}
else:
    results = []
    for obj in meshes:
        m = obj.Mesh
        before_facets = m.CountFacets
        repairs = []
        if {str(fix_degenerates)}:
            m.removeDegenerates()
            repairs.append("removed_degenerates")
        if {str(fix_duplicates)}:
            m.removeDuplicatedFacets()
            repairs.append("removed_duplicates")
        if {str(fix_normals)}:
            m.fixNormals()
            repairs.append("fixed_normals")
        if not repairs:
            # Default: run all standard repairs
            m.removeDegenerates()
            m.removeDuplicatedFacets()
            m.fixNormals()
            repairs = ["removed_degenerates", "removed_duplicates", "fixed_normals"]
        after_facets = m.CountFacets
        obj.Mesh = m
        results.append({{
            "name": obj.Name,
            "facets_before": before_facets,
            "facets_after": after_facets,
            "facets_removed": before_facets - after_facets,
            "repairs": repairs,
        }})
    doc.recompute()
    _fc_result = {{
        "status": "ok",
        "data": {{"results": results}},
        "message": "Repaired {{len(results)}} mesh(es)"
    }}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@mesh_group.command("refine")
@click.option("--name", "-n", help="Specific mesh object to refine.")
@click.option("--iterations", "-i", default=1, type=int,
              help="Number of subdivision iterations.")
@_handle_error
def mesh_refine(name: str | None, iterations: int) -> None:
    """Refine mesh by subdivision."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        name_filter = f'"{name}"' if name else "None"

        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
target_name = {name_filter}
meshes = [obj for obj in doc.Objects if hasattr(obj, "Mesh") and obj.Mesh and (target_name is None or obj.Name == target_name)]
if not meshes:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No mesh objects found"}}
else:
    results = []
    for obj in meshes:
        m = obj.Mesh
        before_facets = m.CountFacets
        for _ in range({iterations}):
            m.subdivide()
        after_facets = m.CountFacets
        obj.Mesh = m
        results.append({{
            "name": obj.Name,
            "facets_before": before_facets,
            "facets_after": after_facets,
            "iterations": {iterations},
        }})
    doc.recompute()
    _fc_result = {{
        "status": "ok",
        "data": {{"results": results}},
        "message": "Refined {{len(results)}} mesh(es)"
    }}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@mesh_group.command("decimate")
@click.option("--name", "-n", help="Specific mesh object to decimate.")
@click.option("--reduction", "-r", default=0.5, type=float,
              help="Reduction factor (0.0-1.0, default 0.5).")
@_handle_error
def mesh_decimate(name: str | None, reduction: float) -> None:
    """Reduce mesh polygon count."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        name_filter = f'"{name}"' if name else "None"

        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
target_name = {name_filter}
meshes = [obj for obj in doc.Objects if hasattr(obj, "Mesh") and obj.Mesh and (target_name is None or obj.Name == target_name)]
if not meshes:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No mesh objects found"}}
else:
    results = []
    for obj in meshes:
        m = obj.Mesh
        before_facets = m.CountFacets
        target_count = int(before_facets * (1.0 - {reduction}))
        m.decimate({reduction})
        after_facets = m.CountFacets
        obj.Mesh = m
        results.append({{
            "name": obj.Name,
            "facets_before": before_facets,
            "facets_after": after_facets,
            "reduction": {reduction},
            "actual_reduction": 1.0 - (after_facets / before_facets) if before_facets > 0 else 0,
        }})
    doc.recompute()
    _fc_result = {{
        "status": "ok",
        "data": {{"results": results}},
        "message": "Decimated {{len(results)}} mesh(es)"
    }}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@mesh_group.command("boolean")
@click.argument("operation", type=click.Choice(["cut", "fuse", "common"]))
@click.argument("base")
@click.argument("tool")
@click.option("--name", "-n", help="Name for the result object.")
@_handle_error
def mesh_boolean(operation: str, base: str, tool: str, name: str | None) -> None:
    """Perform boolean operation on two mesh objects.

    Operations: cut, fuse, common
    """
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or operation.capitalize()

        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
base_obj = doc.getObject("{base}")
tool_obj = doc.getObject("{tool}")
if base_obj is None:
    raise ValueError(f"Base object '{base}' not found")
if tool_obj is None:
    raise ValueError(f"Tool object '{tool}' not found")
if not hasattr(base_obj, "Mesh") or not base_obj.Mesh:
    raise ValueError(f"Base object '{base}' has no mesh")
if not hasattr(tool_obj, "Mesh") or not tool_obj.Mesh:
    raise ValueError(f"Tool object '{tool}' has no mesh")
op = "{operation}"
if op == "fuse":
    result_mesh = base_obj.Mesh.unite(tool_obj.Mesh)
elif op == "cut":
    result_mesh = base_obj.Mesh.cut(tool_obj.Mesh)
elif op == "common":
    result_mesh = base_obj.Mesh.intersect(tool_obj.Mesh)
else:
    raise ValueError(f"Unknown operation: {{op}}")
result_obj = doc.addObject("Mesh::Feature", "{result_name}")
result_obj.Mesh = result_mesh
doc.recompute()
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{result_name}",
        "operation": op,
        "base": "{base}",
        "tool": "{tool}",
        "count_facets": result_mesh.CountFacets,
    }},
    "message": "Boolean {{op}}: {result_name}"
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@mesh_group.command("section")
@click.option("--name", "-n", help="Specific mesh object.")
@click.option("--plane", default="XY", type=click.Choice(["XY", "XZ", "YZ"]),
              help="Section plane (default XY).")
@click.option("--offset", default=0.0, type=float,
              help="Plane offset (default 0).")
@_handle_error
def mesh_section(name: str | None, plane: str, offset: float) -> None:
    """Create a cross-section from a mesh."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        name_filter = f'"{name}"' if name else "None"

        code = f"""\
import FreeCAD
import Mesh
import Part
doc = FreeCAD.ActiveDocument
target_name = {name_filter}
meshes = [obj for obj in doc.Objects if hasattr(obj, "Mesh") and obj.Mesh and (target_name is None or obj.Name == target_name)]
if not meshes:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No mesh objects found"}}
else:
    plane = "{plane}"
    offset = {offset}
    results = []
    for obj in meshes:
        m = obj.Mesh
        if plane == "XY":
            normal = FreeCAD.Vector(0, 0, 1)
        elif plane == "XZ":
            normal = FreeCAD.Vector(0, 1, 0)
        else:
            normal = FreeCAD.Vector(1, 0, 0)
        section = m.crossSections([(FreeCAD.Vector(0, 0, 0), normal)], offset)
        # section is a list of polylines (list of points)
        points = []
        for polyline in section:
            points.extend(polyline)
        results.append({{
            "name": obj.Name,
            "plane": plane,
            "offset": offset,
            "polyline_count": len(section),
            "point_count": len(points),
        }})
    _fc_result = {{
        "status": "ok",
        "data": {{"results": results}},
        "message": "Created sections for {{len(results)}} mesh(es)"
    }}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@mesh_group.command("list")
@_handle_error
def mesh_list() -> None:
    """List all mesh objects in the current document."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = """\
import FreeCAD
doc = FreeCAD.ActiveDocument
meshes = []
for obj in doc.Objects:
    if hasattr(obj, "Mesh") and obj.Mesh:
        m = obj.Mesh
        meshes.append({
            "name": obj.Name,
            "label": obj.Label if hasattr(obj, "Label") else "",
            "count_points": m.CountPoints,
            "count_edges": m.CountEdges,
            "count_facets": m.CountFacets,
            "is_solid": m.isSolid(),
        })
_fc_result = {
    "status": "ok",
    "data": {"meshes": meshes, "count": len(meshes)},
    "message": f"{len(meshes)} mesh object(s)"
}
"""
        r = backend.execute_code(code)
        if r.status == "ok":
            meshes = r.data.get("meshes", [])
            _output.output(r.to_dict(), f"{len(meshes)} mesh object(s):")
        else:
            _output.output(r.to_dict())
    finally:
        backend.disconnect()


@mesh_group.command("info")
@click.argument("name")
@_handle_error
def mesh_info(name: str) -> None:
    """Get detailed information about a mesh object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    _fc_result = {{"status": "error", "data": {{}}, "message": "Object '{name}' not found"}}
elif not hasattr(obj, "Mesh") or not obj.Mesh:
    _fc_result = {{"status": "error", "data": {{}}, "message": "Object '{name}' is not a mesh"}}
else:
    m = obj.Mesh
    bb = m.BoundBox
    _fc_result = {{
        "status": "ok",
        "data": {{
            "name": obj.Name,
            "label": obj.Label if hasattr(obj, "Label") else "",
            "count_points": m.CountPoints,
            "count_edges": m.CountEdges,
            "count_facets": m.CountFacets,
            "is_solid": m.isSolid(),
            "has_non_manifolds": m.hasNonManifolds() if hasattr(m, "hasNonManifolds") else None,
            "has_self_intersections": m.hasSelfIntersections() if hasattr(m, "hasSelfIntersections") else None,
            "bounding_box": {{
                "x": [bb.XMin, bb.XMax],
                "y": [bb.YMin, bb.YMax],
                "z": [bb.ZMin, bb.ZMax],
                "dimensions": [bb.XLength, bb.YLength, bb.ZLength],
                "diagonal": bb.DiagonalLength,
            }},
            "surface_area": m.getSurfaceArea() if hasattr(m, "getSurfaceArea") else None,
            "volume": m.getVolume() if hasattr(m, "getVolume") else None,
        }},
        "message": "Mesh info: {name}"
    }}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@mesh_group.command("create")
@click.argument("mesh_type", default="cube")
@click.option("--name", "-n", help="Mesh name.")
@click.option("--size", default=10.0, type=float, help="Size parameter.")
@_handle_error
def mesh_create(mesh_type: str, name: str | None, size: float) -> None:
    """Create a basic mesh primitive."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        mesh_name = name or f"Mesh_{mesh_type.capitalize()}"
        code = f"""\
import FreeCAD
import Mesh
import Part
doc = FreeCAD.ActiveDocument
if "{mesh_type}" == "cube":
    shape = Part.makeBox({size}, {size}, {size})
elif "{mesh_type}" == "sphere":
    shape = Part.makeSphere({size})
elif "{mesh_type}" == "cylinder":
    shape = Part.makeCylinder({size}, {size} * 2)
else:
    shape = Part.makeBox({size}, {size}, {size})
mesh = Mesh.Mesh(shape.tessellate(0.1))
obj = doc.addObject("Mesh::Feature", "{mesh_name}")
obj.Mesh = mesh
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{mesh_name}", "type": "{mesh_type}", "count_points": mesh.CountPoints, "count_facets": mesh.CountFacets}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created mesh: {mesh_name}")
    finally:
        backend.disconnect()


@mesh_group.command("evaluate")
@click.argument("name")
@_handle_error
def mesh_evaluate(name: str) -> None:
    """Evaluate mesh quality."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Mesh '{name}' not found")
mesh = obj.Mesh
bb = mesh.BoundBox
_fc_result = {{"status": "ok", "data": {{"name": "{name}", "count_points": mesh.CountPoints, "count_edges": mesh.CountEdges, "count_facets": mesh.CountFacets, "is_solid": mesh.isSolid(), "bounding_box": {{"x": [bb.XMin, bb.XMax], "y": [bb.YMin, bb.YMax], "z": [bb.ZMin, bb.ZMax]}}}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"Mesh quality: {name}")
    finally:
        backend.disconnect()


@mesh_group.command("flip-normals")
@click.argument("name")
@_handle_error
def mesh_flip_normals(name: str) -> None:
    """Flip mesh normals."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Mesh '{name}' not found")
obj.Mesh.flipNormals()
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{name}", "flipped": True}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Flipped normals: {name}")
    finally:
        backend.disconnect()


@mesh_group.command("smooth")
@click.argument("name")
@click.option("--iterations", default=3, type=int, help="Smoothing iterations.")
@click.option("--factor", default=0.5, type=float, help="Smoothing factor.")
@_handle_error
def mesh_smooth(name: str, iterations: int, factor: float) -> None:
    """Smooth a mesh."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Mesh '{name}' not found")
mesh = obj.Mesh
mesh.smooth({iterations}, {factor})
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{name}", "iterations": {iterations}}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Smoothed mesh: {name}")
    finally:
        backend.disconnect()
