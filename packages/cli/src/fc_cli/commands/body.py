"""PartDesign body commands.

Commands for PartDesign features:
  body new           — Create a new PartDesign body
  body pad           — Add a pad (extrusion) feature
  body pocket        — Add a pocket (cut extrusion) feature
  body fillet        — Add a fillet feature
  body chamfer       — Add a chamfer feature
  body revolution    — Add a revolution feature
  body groove        — Add a groove (subtractive revolution) feature
  body list          — List all bodies
  body get           — Get body details
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


@click.group("body")
def body_group():
    """PartDesign body commands."""
    pass


@body_group.command("new")
@click.option("--name", "-n", help="Body name.")
@_handle_error
def body_new(name: str | None) -> None:
    """Create a new PartDesign body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.body_new(name or "Body")
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@body_group.command("pad")
@click.argument("body_name")
@click.argument("sketch_name")
@click.option("--length", "-l", default=10.0, type=float, help="Pad length.")
@click.option("--symmetric", is_flag=True, help="Symmetric pad.")
@click.option("--reversed", "is_reversed", is_flag=True, help="Reverse direction.")
@_handle_error
def body_pad(body_name: str, sketch_name: str, length: float,
             symmetric: bool, is_reversed: bool) -> None:
    """Add a pad (extrusion) feature to a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.body_pad(body_name, sketch_name, length,
                             symmetric=symmetric, reversed=is_reversed)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@body_group.command("pocket")
@click.argument("body_name")
@click.argument("sketch_name")
@click.option("--length", "-l", default=5.0, type=float, help="Pocket depth.")
@click.option("--symmetric", is_flag=True, help="Symmetric pocket.")
@click.option("--reversed", "is_reversed", is_flag=True, help="Reverse direction.")
@_handle_error
def body_pocket(body_name: str, sketch_name: str, length: float,
                symmetric: bool, is_reversed: bool) -> None:
    """Add a pocket (cut extrusion) feature to a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
sketch = doc.getObject("{sketch_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
pocket = body.newObject("PartDesign::Pocket", "Pocket")
pocket.Profile = sketch
pocket.Length = {length}
pocket.Symmetric = {"true" if symmetric else "false"}
pocket.Reversed = {"true" if is_reversed else "false"}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added pocket: depth={length}")
    finally:
        backend.disconnect()


@body_group.command("fillet")
@click.argument("body_name")
@click.option("--radius", "-r", default=1.0, type=float, help="Fillet radius.")
@click.option("--edges", default="all", help="Edges: 'all' or comma-sep indices.")
@_handle_error
def body_fillet(body_name: str, radius: float, edges: str) -> None:
    """Add a fillet feature to a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        edge_list = "None" if edges == "all" else f"[{edges}]"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
fillet = body.newObject("PartDesign::Fillet", "Fillet")
fillet.Radius = {radius}
if {edge_list} is not None:
    fillet.Base = (body, {edge_list})
else:
    fillet.Base = body
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added fillet: radius={radius}")
    finally:
        backend.disconnect()


@body_group.command("chamfer")
@click.argument("body_name")
@click.option("--size", "-s", default=1.0, type=float, help="Chamfer size.")
@click.option("--edges", default="all", help="Edges: 'all' or comma-sep indices.")
@_handle_error
def body_chamfer(body_name: str, size: float, edges: str) -> None:
    """Add a chamfer feature to a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        edge_list = "None" if edges == "all" else f"[{edges}]"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
chamfer = body.newObject("PartDesign::Chamfer", "Chamfer")
chamfer.Size = {size}
if {edge_list} is not None:
    chamfer.Base = (body, {edge_list})
else:
    chamfer.Base = body
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added chamfer: size={size}")
    finally:
        backend.disconnect()


@body_group.command("revolution")
@click.argument("body_name")
@click.argument("sketch_name")
@click.option("--angle", "-a", default=360.0, type=float, help="Revolution angle.")
@click.option("--axis", default="Z", type=click.Choice(["X", "Y", "Z"]),
              help="Revolution axis.")
@click.option("--reversed", "is_reversed", is_flag=True, help="Reverse direction.")
@_handle_error
def body_revolution(body_name: str, sketch_name: str, angle: float,
                    axis: str, is_reversed: bool) -> None:
    """Add a revolution feature to a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        axis_vec = {"X": "1,0,0", "Y": "0,1,0", "Z": "0,0,1"}[axis]
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
sketch = doc.getObject("{sketch_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
rev = body.newObject("PartDesign::Revolution", "Revolution")
rev.Profile = sketch
rev.ReferenceAxis = (sketch, ['{axis}Axis'])
rev.Reversed = {"true" if is_reversed else "false"}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added revolution: angle={angle}°")
    finally:
        backend.disconnect()


@body_group.command("groove")
@click.argument("body_name")
@click.argument("sketch_name")
@click.option("--angle", "-a", default=360.0, type=float, help="Groove angle.")
@click.option("--axis", default="Z", type=click.Choice(["X", "Y", "Z"]),
              help="Revolution axis.")
@click.option("--reversed", "is_reversed", is_flag=True, help="Reverse direction.")
@_handle_error
def body_groove(body_name: str, sketch_name: str, angle: float,
                axis: str, is_reversed: bool) -> None:
    """Add a groove (subtractive revolution) feature."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
sketch = doc.getObject("{sketch_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
groove = body.newObject("PartDesign::Groove", "Groove")
groove.Profile = sketch
groove.ReferenceAxis = (sketch, ['{axis}Axis'])
groove.Reversed = {"true" if is_reversed else "false"}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added groove: angle={angle}°")
    finally:
        backend.disconnect()


@body_group.command("list")
@_handle_error
def body_list() -> None:
    """List all bodies."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = """\
import FreeCAD
doc = FreeCAD.ActiveDocument
bodies = [obj for obj in doc.Objects if obj.TypeId == "PartDesign::Body"]
_fc_result = {
    "status": "ok",
    "data": {"bodies": [{"name": b.Name, "label": b.Label} for b in bodies], "count": len(bodies)},
    "message": ""
}
"""
        r = backend.execute_code(code)
        count = r.data.get("data", {}).get("count", 0)
        _output.output(r.to_dict(), f"{count} body/bodies:")
    finally:
        backend.disconnect()


@body_group.command("get")
@click.argument("name")
@_handle_error
def body_get(name: str) -> None:
    """Get body details."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{name}")
if body is None:
    raise ValueError(f"Body '{name}' not found")
features = [{{"name": f.Name, "label": f.Label, "type_id": f.TypeId}} for f in body.Group]
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": body.Name,
        "label": body.Label,
        "features": features,
        "feature_count": len(features),
    }},
    "message": ""
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"Body '{name}':")
    finally:
        backend.disconnect()


@body_group.command("pattern-linear")
@click.argument("body_name")
@click.argument("feature_name")
@click.option("--direction", "-d", default="X", type=click.Choice(["X", "Y", "Z"]),
              help="Pattern direction.")
@click.option("--count", "-c", default=3, type=int, help="Number of instances.")
@click.option("--spacing", "-s", default=10.0, type=float, help="Spacing between instances.")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_pattern_linear(body_name: str, feature_name: str, direction: str,
                        count: int, spacing: float, name: str | None) -> None:
    """Create a linear pattern of a feature in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or f"{feature_name}_LinearPattern"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
feature = body.getObject("{feature_name}")
if feature is None:
    raise ValueError(f"Feature '{feature_name}' not found in body '{body_name}'")
pattern = body.newObject("PartDesign::LinearPattern", "{result_name}")
pattern.Originals = [feature]
pattern.Direction = (feature, ['{direction}Axis'])
pattern.Length = {spacing * (count - 1)}
pattern.Occurrences = {count}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created linear pattern: {result_name} ({count}x {direction})")
    finally:
        backend.disconnect()


@body_group.command("pattern-polar")
@click.argument("body_name")
@click.argument("feature_name")
@click.option("--axis", "-a", default="Z", type=click.Choice(["X", "Y", "Z"]),
              help="Rotation axis.")
@click.option("--count", "-c", default=6, type=int, help="Number of instances.")
@click.option("--angle", default=360.0, type=float, help="Total angle (degrees).")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_pattern_polar(body_name: str, feature_name: str, axis: str,
                       count: int, angle: float, name: str | None) -> None:
    """Create a polar (circular) pattern of a feature in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or f"{feature_name}_PolarPattern"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
feature = body.getObject("{feature_name}")
if feature is None:
    raise ValueError(f"Feature '{feature_name}' not found in body '{body_name}'")
pattern = body.newObject("PartDesign::PolarPattern", "{result_name}")
pattern.Originals = [feature]
pattern.Axis = (feature, ['{axis}Axis'])
pattern.Angle = {angle}
pattern.Occurrences = {count}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created polar pattern: {result_name} ({count}x {angle}deg)")
    finally:
        backend.disconnect()


@body_group.command("pattern-mirror")
@click.argument("body_name")
@click.argument("feature_name")
@click.option("--plane", "-p", default="XY", type=click.Choice(["XY", "XZ", "YZ"]),
              help="Mirror plane.")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_pattern_mirror(body_name: str, feature_name: str, plane: str,
                        name: str | None) -> None:
    """Create a mirrored pattern of a feature in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or f"{feature_name}_MirrorPattern"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
feature = body.getObject("{feature_name}")
if feature is None:
    raise ValueError(f"Feature '{feature_name}' not found in body '{body_name}'")
pattern = body.newObject("PartDesign::MirroredPattern", "{result_name}")
pattern.Originals = [feature]
pattern.MirrorPlane = (feature, ['{plane}Plane'])
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created mirror pattern: {result_name} (plane={plane})")
    finally:
        backend.disconnect()


@body_group.command("hole")
@click.argument("body_name")
@click.argument("sketch_name")
@click.option("--type", "hole_type", default="simple",
              type=click.Choice(["simple", "counterbore", "countersink", "threaded"]),
              help="Hole type.")
@click.option("--diameter", "-d", default=5.0, type=float, help="Hole diameter.")
@click.option("--depth", default=10.0, type=float, help="Hole depth.")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_hole(body_name: str, sketch_name: str, hole_type: str,
              diameter: float, depth: float, name: str | None) -> None:
    """Add a hole feature to a body based on a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "Hole"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
sketch = doc.getObject("{sketch_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
hole = body.newObject("PartDesign::Hole", "{result_name}")
hole.Profile = sketch
hole.Diameter = {diameter}
hole.Depth = {depth}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created hole: {result_name} (diameter={diameter}mm, type={hole_type})")
    finally:
        backend.disconnect()


@body_group.command("shell")
@click.argument("body_name")
@click.option("--thickness", "-t", default=2.0, type=float, help="Shell thickness.")
@click.option("--faces", "-f", help="Faces to remove as comma-sep indices.")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_shell(body_name: str, thickness: float, faces: str | None,
               name: str | None) -> None:
    """Create a shell (hollow) from a solid body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "Shell"
        face_list = f"[{faces}]" if faces else "None"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
shell = body.newObject("PartDesign::Thickness", "{result_name}")
shell.Base = (body, {face_list})
shell.Value = {thickness}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created shell: {result_name} (thickness={thickness}mm)")
    finally:
        backend.disconnect()


@body_group.command("draft")
@click.argument("body_name")
@click.option("--angle", "-a", default=5.0, type=float, help="Draft angle (degrees).")
@click.option("--faces", "-f", required=True, help="Faces as comma-sep indices.")
@click.option("--plane", "-p", default="XY", type=click.Choice(["XY", "XZ", "YZ"]),
              help="Neutral plane.")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_draft(body_name: str, angle: float, faces: str,
               plane: str, name: str | None) -> None:
    """Add a draft angle to selected faces of a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "Draft"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
draft = body.newObject("PartDesign::Draft", "{result_name}")
draft.Base = (body, [{faces}])
draft.Angle = {angle}
draft.NeutralPlane = (body, ['{plane}Plane'])
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created draft: {result_name} (angle={angle}deg)")
    finally:
        backend.disconnect()


@body_group.command("datum-plane")
@click.argument("body_name")
@click.option("--name", "-n", default="DatumPlane", help="Datum plane name.")
@click.option("--plane", "-p", default="XY", type=click.Choice(["XY", "XZ", "YZ"]),
              help="Reference plane.")
@click.option("--offset", default=0.0, type=float, help="Offset from reference plane.")
@click.option("--rotation", default="0,0,0", help="Rotation as rx,ry,rz degrees.")
@_handle_error
def body_datum_plane(body_name: str, name: str, plane: str,
                     offset: float, rotation: str) -> None:
    """Create a datum (reference) plane in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        rx, ry, rz = [float(x) for x in rotation.split(",")]
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
datum = body.newObject("PartDesign::Plane", "{name}")
datum.Placement = FreeCAD.Placement(FreeCAD.Vector(0, 0, {offset}), FreeCAD.Rotation({rx}, {ry}, {rz}))
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created datum plane: {name} (offset={offset}mm)")
    finally:
        backend.disconnect()


@body_group.command("datum-point")
@click.argument("body_name")
@click.option("--name", "-n", default="DatumPoint", help="Datum point name.")
@click.option("--position", "-pos", default="0,0,0", help="Position as x,y,z.")
@_handle_error
def body_datum_point(body_name: str, name: str, position: str) -> None:
    """Create a datum (reference) point in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py, pz = [float(x) for x in position.split(",")]
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
datum = body.newObject("PartDesign::Point", "{name}")
datum.Placement = FreeCAD.Placement(FreeCAD.Vector({px}, {py}, {pz}), FreeCAD.Rotation())
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created datum point: {name} at ({px},{py},{pz})")
    finally:
        backend.disconnect()


@body_group.command("datum-line")
@click.argument("body_name")
@click.option("--name", "-n", default="DatumLine", help="Datum line name.")
@click.option("--direction", "-d", default="Z", type=click.Choice(["X", "Y", "Z"]),
              help="Line direction.")
@click.option("--position", "-pos", default="0,0,0", help="Position as x,y,z.")
@_handle_error
def body_datum_line(body_name: str, name: str, direction: str, position: str) -> None:
    """Create a datum (reference) line in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py, pz = [float(x) for x in position.split(",")]
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
datum = body.newObject("PartDesign::Line", "{name}")
datum.Placement = FreeCAD.Placement(FreeCAD.Vector({px}, {py}, {pz}), FreeCAD.Rotation())
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created datum line: {name} (dir={direction})")
    finally:
        backend.disconnect()


@body_group.command("set-tip")
@click.argument("body_name")
@click.option("--feature", "-f", help="Feature name to set as tip. Empty = reset to last.")
@_handle_error
def body_set_tip(body_name: str, feature: str | None) -> None:
    """Set the tip (current modeling position) of a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        if feature:
            code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
feat = body.getObject("{feature}")
if feat is None:
    raise ValueError(f"Feature '{feature}' not found in body '{body_name}'")
body.Tip = feat
doc.recompute()
"""
        else:
            code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
if body.Group:
    body.Tip = body.Group[-1]
doc.recompute()
"""
        r = backend.execute_code(code)
        tip_name = feature or "last feature"
        _output.output(r.to_dict(), r.message or f"Set tip of '{body_name}' to '{tip_name}'")
    finally:
        backend.disconnect()


@body_group.command("remove-feature")
@click.argument("body_name")
@click.argument("feature_name")
@_handle_error
def body_remove_feature(body_name: str, feature_name: str) -> None:
    """Remove a feature from a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
feat = body.getObject("{feature_name}")
if feat is None:
    raise ValueError(f"Feature '{feature_name}' not found in body '{body_name}'")
body.removeObject(feat)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Removed feature '{feature_name}' from '{body_name}'")
    finally:
        backend.disconnect()
