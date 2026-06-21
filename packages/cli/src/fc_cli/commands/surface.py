"""Surface commands.

Commands for Surface workbench operations:
  surface loft       — Create a loft through profiles
  surface sweep      — Create a sweep along a path
  surface fill       — Fill a boundary with a surface
  surface pipe       — Create a pipe surface
  surface offset     — Create an offset surface
  surface thicken    — Thicken a surface into a solid
  surface flatten    — Flatten a surface
  surface sew        — Sew surfaces together
  surface list       — List all surface objects
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


@click.group("surface")
def surface_group():
    """Surface workbench commands."""
    pass


@surface_group.command("loft")
@click.option("--profiles", "-p", required=True,
              help="Semicolon-separated object names (e.g. 'Sketch;Sketch001').")
@click.option("--solid", is_flag=True, default=False,
              help="Create a solid loft.")
@click.option("--ruled", is_flag=True, default=False,
              help="Create a ruled loft.")
@click.option("--name", "-n", help="Result object name.")
@_handle_error
def surface_loft(profiles: str, solid: bool, ruled: bool,
                 name: str | None) -> None:
    """Create a loft through profile shapes."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        profile_list = [f'"{p.strip()}"' for p in profiles.split(";") if p.strip()]
        profiles_code = ", ".join(profile_list)
        result_name = name or "Loft"

        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
profiles = []
for pname in [{profiles_code}]:
    obj = doc.getObject(pname)
    if obj is None:
        raise ValueError(f"Object '{{pname}}' not found")
    if hasattr(obj, "Shape") and obj.Shape:
        profiles.append(obj.Shape)
    else:
        raise ValueError(f"Object '{{pname}}' has no Shape")
if len(profiles) < 2:
    raise ValueError("At least 2 profiles required for loft")
loft = Part.makeLoft(profiles, solid={solid}, ruled={ruled})
result = doc.addObject("Part::Feature", "{result_name}")
result.Shape = loft
doc.recompute()
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{result_name}",
        "profiles": [{profiles_code}],
        "solid": {solid},
        "ruled": {ruled},
    }},
    "message": "Created loft: {result_name}"
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@surface_group.command("sweep")
@click.option("--profile", "-p", required=True,
              help="Profile object name.")
@click.option("--path", required=True,
              help="Path object name (edge or wire).")
@click.option("--solid", is_flag=True, default=False,
              help="Create a solid sweep.")
@click.option("--name", "-n", help="Result object name.")
@_handle_error
def surface_sweep(profile: str, path: str, solid: bool,
                  name: str | None) -> None:
    """Create a sweep along a path."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "Sweep"

        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
prof_obj = doc.getObject("{profile}")
if prof_obj is None:
    raise ValueError(f"Profile object '{profile}' not found")
path_obj = doc.getObject("{path}")
if path_obj is None:
    raise ValueError(f"Path object '{path}' not found")
# Extract the wire/edge from profile and path
prof_shape = prof_obj.Shape if hasattr(prof_obj, "Shape") else None
path_shape = path_obj.Shape if hasattr(path_obj, "Shape") else None
if prof_shape is None:
    raise ValueError(f"Profile object has no Shape")
if path_shape is None:
    raise ValueError(f"Path object has no Shape")
# Find wires
prof_wires = prof_shape.Wires if prof_shape.Wires else [prof_shape.Edges[0]]
path_wires = path_shape.Wires if path_shape.Wires else [path_shape.Edges[0]]
sweep = Part.makePipeShell(path_wires[0], [prof_wires[0]], {solid})
result = doc.addObject("Part::Feature", "{result_name}")
result.Shape = sweep
doc.recompute()
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{result_name}",
        "profile": "{profile}",
        "path": "{path}",
        "solid": {solid},
    }},
    "message": "Created sweep: {result_name}"
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@surface_group.command("fill")
@click.option("--edges", "-e", required=True,
              help="Semicolon-separated edge references (e.g. 'Box.Edge1;Box.Edge2').")
@click.option("--degree", default=3, type=int,
              help="Maximum surface degree (default 3).")
@click.option("--name", "-n", help="Result object name.")
@_handle_error
def surface_fill(edges: str, degree: int, name: str | None) -> None:
    """Fill a boundary with a surface."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "Fill"
        edge_refs = [e.strip() for e in edges.split(";") if e.strip()]

        code_lines = [
            'import FreeCAD',
            'import Part',
            'doc = FreeCAD.ActiveDocument',
            'edge_objects = []',
        ]
        for ref in edge_refs:
            obj_name, edge_name = ref.rsplit(".", 1)
            code_lines.append(f'obj = doc.getObject("{obj_name}")')
            code_lines.append(f'if obj is None:')
            code_lines.append(f'    raise ValueError(f"Object \'{obj_name}\' not found")')
            code_lines.append(f'shape = obj.Shape')
            code_lines.append(f'edge = shape.{edge_name}')
            code_lines.append(f'edge_objects.append(edge)')

        code_lines.extend([
            f'surf = Part.Face(Part.makeFilledFace(edge_objects, MaxDegree={degree}))',
            f'result = doc.addObject("Part::Feature", "{result_name}")',
            f'result.Shape = Part.makeShell([surf]) if hasattr(Part, "makeShell") else surf',
            f'doc.recompute()',
            f'_fc_result = {{',
            f'    "status": "ok",',
            f'    "data": {{',
            f'        "name": "{result_name}",',
            f'        "edges": {edge_refs},',
            f'        "degree": {degree},',
            f'    }},',
            f'    "message": "Created fill surface: {result_name}"',
            f'}}',
        ])

        r = backend.execute_code("\n".join(code_lines))
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@surface_group.command("pipe")
@click.option("--path", "-p", required=True,
              help="Path object name (edge or wire).")
@click.option("--radius", "-r", default=2.0, type=float,
              help="Pipe radius (default 2).")
@click.option("--name", "-n", help="Result object name.")
@_handle_error
def surface_pipe(path: str, radius: float, name: str | None) -> None:
    """Create a pipe surface along a path."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "Pipe"

        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
path_obj = doc.getObject("{path}")
if path_obj is None:
    raise ValueError(f"Path object '{path}' not found")
path_shape = path_obj.Shape if hasattr(path_obj, "Shape") else None
if path_shape is None:
    raise ValueError(f"Path object has no Shape")
wires = path_shape.Wires if path_shape.Wires else [path_shape.Edges[0]]
pipe = Part.makePipe(wires[0], {radius})
result = doc.addObject("Part::Feature", "{result_name}")
result.Shape = pipe
doc.recompute()
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{result_name}",
        "path": "{path}",
        "radius": {radius},
    }},
    "message": "Created pipe: {result_name} (radius={radius})"
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@surface_group.command("offset")
@click.argument("name")
@click.option("--distance", "-d", default=1.0, type=float,
              help="Offset distance (default 1).")
@click.option("--name", "-n", "result_name", help="Result object name.")
@_handle_error
def surface_offset(name: str, distance: float,
                   result_name: str | None) -> None:
    """Create an offset surface."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Offset"

        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if not hasattr(obj, "Shape") or not obj.Shape:
    raise ValueError(f"Object '{name}' has no Shape")
faces = obj.Shape.Faces
if not faces:
    raise ValueError(f"Object '{name}' has no faces")
offset_shapes = []
for face in faces:
    offset_shapes.append(face.makeOffsetShape({distance}, 0.01))
if len(offset_shapes) == 1:
    result_shape = offset_shapes[0]
else:
    result_shape = Part.makeCompound(offset_shapes)
result = doc.addObject("Part::Feature", "{out_name}")
result.Shape = result_shape
doc.recompute()
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{out_name}",
        "source": "{name}",
        "distance": {distance},
    }},
    "message": "Created offset surface: {out_name} (distance={distance})"
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@surface_group.command("thicken")
@click.argument("name")
@click.option("--thickness", "-t", default=1.0, type=float,
              help="Thickness value (default 1).")
@click.option("--direction", default="both",
              type=click.Choice(["both", "single"]),
              help="Thicken direction: both or single (default both).")
@click.option("--name", "-n", "result_name", help="Result object name.")
@_handle_error
def surface_thicken(name: str, thickness: float, direction: str,
                    result_name: str | None) -> None:
    """Thicken a surface into a solid."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Thickened"
        both = "True" if direction == "both" else "False"

        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if not hasattr(obj, "Shape") or not obj.Shape:
    raise ValueError(f"Object '{name}' has no Shape")
faces = obj.Shape.Faces
if not faces:
    raise ValueError(f"Object '{name}' has no faces")
thickened = obj.Shape.makeThickSolid(faces, {thickness}, tolerance=0.01, intersection={both}, closing=False)
result = doc.addObject("Part::Feature", "{out_name}")
result.Shape = thickened
doc.recompute()
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{out_name}",
        "source": "{name}",
        "thickness": {thickness},
        "direction": "{direction}",
    }},
    "message": "Thickened surface: {out_name} (thickness={thickness}, direction={direction})"
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@surface_group.command("flatten")
@click.argument("name")
@click.option("--tolerance", default=0.01, type=float,
              help="Flatten tolerance (default 0.01).")
@click.option("--name", "-n", "result_name", help="Result object name.")
@_handle_error
def surface_flatten(name: str, tolerance: float,
                    result_name: str | None) -> None:
    """Flatten a surface to a plane."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Flattened"

        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if not hasattr(obj, "Shape") or not obj.Shape:
    raise ValueError(f"Object '{name}' has no Shape")
faces = obj.Shape.Faces
if not faces:
    raise ValueError(f"Object '{name}' has no faces")
# Approximate the surface with a B-spline and flatten
# Use Part.flatmesh or project to XY plane
flattened_wires = []
for face in faces:
    # Get the face boundary wires
    for wire in face.Wires:
        verts = wire.OrderedVertexes if hasattr(wire, "OrderedVertexes") else wire.Vertexes
        pts = [FreeCAD.Vector(v.X, v.Y, 0) for v in verts]
        if len(pts) > 2:
            flattened_wires.append(Part.makePolygon(pts))
if flattened_wires:
    shell = Part.makeShell(flattened_wires) if len(flattened_wires) > 1 else Part.Face(flattened_wires[0])
    result_shape = shell
else:
    raise ValueError("Failed to flatten: no wires extracted")
result = doc.addObject("Part::Feature", "{out_name}")
result.Shape = result_shape
doc.recompute()
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{out_name}",
        "source": "{name}",
        "tolerance": {tolerance},
    }},
    "message": "Flattened surface: {out_name}"
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@surface_group.command("sew")
@click.option("--objects", "-o", required=True,
              help="Semicolon-separated object names to sew.")
@click.option("--tolerance", default=0.01, type=float,
              help="Sewing tolerance (default 0.01).")
@click.option("--name", "-n", help="Result object name.")
@_handle_error
def surface_sew(objects: str, tolerance: float, name: str | None) -> None:
    """Sew surfaces together."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "Sew"
        obj_names = [o.strip() for o in objects.split(";") if o.strip()]
        obj_list_code = ", ".join(f'"{n}"' for n in obj_names)

        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj_names = [{obj_list_code}]
shapes = []
for oname in obj_names:
    obj = doc.getObject(oname)
    if obj is None:
        raise ValueError(f"Object '{{oname}}' not found")
    if not hasattr(obj, "Shape") or not obj.Shape:
        raise ValueError(f"Object '{{oname}}' has no Shape")
    shapes.append(obj.Shape)
if len(shapes) < 2:
    raise ValueError("At least 2 surfaces required for sewing")
shell = Part.Shell([])
for s in shapes:
    for face in s.Faces:
        shell.addFace(face)
sewed = shell.sewShape()
result = doc.addObject("Part::Feature", "{result_name}")
result.Shape = sewed
doc.recompute()
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{result_name}",
        "objects": {obj_names},
        "tolerance": {tolerance},
    }},
    "message": "Sewed surfaces: {result_name}"
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@surface_group.command("list")
@_handle_error
def surface_list() -> None:
    """List all surface objects in the current document."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = """\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
surface_objects = []
for obj in doc.Objects:
    if hasattr(obj, "Shape") and obj.Shape:
        shape = obj.Shape
        # Classify as surface-like (shell or face, not solid)
        if shape.ShapeType in ("Shell", "Face", "Compound"):
            info = {
                "name": obj.Name,
                "label": obj.Label if hasattr(obj, "Label") else "",
                "type_id": obj.TypeId,
                "shape_type": shape.ShapeType,
                "area": shape.Area if hasattr(shape, "Area") else None,
                "faces": len(shape.Faces) if hasattr(shape, "Faces") else None,
            }
            surface_objects.append(info)
        elif shape.ShapeType == "Solid":
            # Check if it's a surface solid (very thin)
            if hasattr(shape, "Shells") and shape.Shells:
                info = {
                    "name": obj.Name,
                    "label": obj.Label if hasattr(obj, "Label") else "",
                    "type_id": obj.TypeId,
                    "shape_type": shape.ShapeType,
                    "area": shape.Area,
                    "volume": shape.Volume,
                    "faces": len(shape.Faces),
                }
                surface_objects.append(info)
_fc_result = {
    "status": "ok",
    "data": {"objects": surface_objects, "count": len(surface_objects)},
    "message": ""
}
"""
        r = backend.execute_code(code)
        if r.status == "ok":
            objects = r.data.get("objects", r.data.get("data", {}).get("objects", []))
            _output.output(r.to_dict(), f"{len(objects)} surface/object(s):")
        else:
            _output.output(r.to_dict())
    finally:
        backend.disconnect()


@surface_group.command("extrude")
@click.argument("name")
@click.option("--direction", "-d", default="0,0,10", help="Extrude direction as x,y,z.")
@click.option("--name", "-n", "result_name", help="Result object name.")
@_handle_error
def surface_extrude(name: str, direction: str, result_name: str | None) -> None:
    """Extrude a face or wire into a surface/solid."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        dx, dy, dz = [float(x) for x in direction.split(",")]
        out_name = result_name or f"{name}_Extruded"
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if not hasattr(obj, "Shape") or not obj.Shape:
    raise ValueError(f"Object '{name}' has no Shape")
shape = obj.Shape
dir_vec = FreeCAD.Vector({dx}, {dy}, {dz})
if shape.Faces:
    extruded = shape.Faces[0].extrude(dir_vec)
elif shape.Wires:
    extruded = shape.Wires[0].makeOffsetShape(dir_vec.Length, 0.01)
else:
    raise ValueError("Object has no faces or wires to extrude")
result = doc.addObject("Part::Feature", "{out_name}")
result.Shape = extruded
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{out_name}", "direction": [{dx}, {dy}, {dz}]}}, "message": "Created extruded surface: {out_name}"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@surface_group.command("revolve")
@click.argument("name")
@click.option("--axis", "-a", default="0,0,0,1,0,0",
              help="Axis as ox,oy,oz,dx,dy,dz.")
@click.option("--angle", default=360.0, type=float, help="Revolution angle (degrees).")
@click.option("--name", "-n", "result_name", help="Result object name.")
@_handle_error
def surface_revolve(name: str, axis: str, angle: float,
                    result_name: str | None) -> None:
    """Revolve a profile around an axis to create a surface."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        parts = [float(x) for x in axis.split(",")]
        ox, oy, oz, dx, dy, dz = parts
        out_name = result_name or f"{name}_Revolved"
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if not hasattr(obj, "Shape") or not obj.Shape:
    raise ValueError(f"Object '{name}' has no Shape")
shape = obj.Shape
axis_origin = FreeCAD.Vector({ox}, {oy}, {oz})
axis_dir = FreeCAD.Vector({dx}, {dy}, {dz})
if shape.Wires:
    revolved = shape.Wires[0].revolve(axis_origin, axis_dir, {angle})
elif shape.Faces:
    revolved = shape.Faces[0].revolve(axis_origin, axis_dir, {angle})
else:
    raise ValueError("Object has no faces or wires to revolve")
result = doc.addObject("Part::Feature", "{out_name}")
result.Shape = revolved
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{out_name}", "angle": {angle}}}, "message": "Created revolved surface: {out_name}"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@surface_group.command("ruled")
@click.argument("wire1_name")
@click.argument("wire2_name")
@click.option("--name", "-n", help="Result object name.")
@_handle_error
def surface_ruled(wire1_name: str, wire2_name: str, name: str | None) -> None:
    """Create a ruled surface between two wires."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "RuledSurface"
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj1 = doc.getObject("{wire1_name}")
obj2 = doc.getObject("{wire2_name}")
if obj1 is None:
    raise ValueError(f"Object '{wire1_name}' not found")
if obj2 is None:
    raise ValueError(f"Object '{wire2_name}' not found")
w1 = obj1.Shape.Wires[0] if obj1.Shape.Wires else None
w2 = obj2.Shape.Wires[0] if obj2.Shape.Wires else None
if w1 is None or w2 is None:
    raise ValueError("Both objects must have wires")
ruled = Part.makeRuledSurface(w1, w2)
result = doc.addObject("Part::Feature", "{result_name}")
result.Shape = ruled
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{result_name}", "wire1": "{wire1_name}", "wire2": "{wire2_name}"}}, "message": "Created ruled surface: {result_name}"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@surface_group.command("curvature")
@click.argument("name")
@click.option("--face-index", default=0, type=int, help="Face index to analyze.")
@_handle_error
def surface_curvature(name: str, face_index: int) -> None:
    """Analyze curvature of a surface."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if not hasattr(obj, "Shape") or not obj.Shape:
    raise ValueError(f"Object '{name}' has no Shape")
faces = obj.Shape.Faces
if not faces:
    raise ValueError(f"Object '{name}' has no faces")
if {face_index} >= len(faces):
    raise ValueError(f"Face index {face_index} out of range (0-{{len(faces)-1}})")
face = faces[{face_index}]
surf = face.Surface
bb = face.BoundBox
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{name}",
        "face_index": {face_index},
        "surface_type": type(surf).__name__,
        "area": face.Area,
        "bounds": {{"x": [bb.XMin, bb.XMax], "y": [bb.YMin, bb.YMax], "z": [bb.ZMin, bb.ZMax]}},
    }},
    "message": ""
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"Curvature analysis for {name}:")
    finally:
        backend.disconnect()
