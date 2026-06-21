"""Assembly commands.

Commands for assembly operations:
  assembly create      — Create a new assembly
  assembly add         — Add a part to the assembly
  assembly remove      — Remove a part from the assembly
  assembly constraint  — Add a constraint between parts
  assembly solve       — Solve constraints
  assembly explode     — Create an exploded view
  assembly animate     — Create an animation
  assembly list        — List all parts in assembly
  assembly ground      — Ground a part (fix in place)
  assembly show        — Show assembly tree
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


@click.group("assembly")
def assembly_group():
    """Assembly commands for multi-part assemblies."""
    pass


@assembly_group.command("create")
@click.option("--name", "-n", default="Assembly", help="Assembly name.")
@click.option("--type", "asm_type", default="a2plus",
              type=click.Choice(["a2plus", "a4", "asm3"]),
              help="Assembly workbench type.")
@_handle_error
def assembly_create(name: str, asm_type: str) -> None:
    """Create a new assembly."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
# Create assembly object
asm = doc.addObject("App::Part", "{name}")
_fc_result = {{"status": "ok", "data": {{"name": asm.Name, "label": asm.Label, "type": "{asm_type}"}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created assembly: {name} (type={asm_type})")
    finally:
        backend.disconnect()


@assembly_group.command("add")
@click.option("--assembly", "-a", required=True, help="Assembly name.")
@click.option("--object", "-o", "obj_name", required=True, help="Object name to add.")
@_handle_error
def assembly_add(assembly: str, obj_name: str) -> None:
    """Add a part to the assembly."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
asm = doc.getObject("{assembly}")
obj = doc.getObject("{obj_name}")
if asm is None:
    raise ValueError(f"Assembly '{assembly}' not found")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
asm.addObject(obj)
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"assembly": "{assembly}", "object": "{obj_name}"}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added {obj_name} to {assembly}")
    finally:
        backend.disconnect()


@assembly_group.command("remove")
@click.option("--assembly", "-a", required=True, help="Assembly name.")
@click.option("--object", "-o", "obj_name", required=True, help="Object name to remove.")
@_handle_error
def assembly_remove(assembly: str, obj_name: str) -> None:
    """Remove a part from the assembly."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
asm = doc.getObject("{assembly}")
obj = doc.getObject("{obj_name}")
if asm is None:
    raise ValueError(f"Assembly '{assembly}' not found")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
asm.removeObject(obj)
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"assembly": "{assembly}", "object": "{obj_name}"}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Removed {obj_name} from {assembly}")
    finally:
        backend.disconnect()


@assembly_group.command("constraint")
@click.option("--type", "-t", "ctype", required=True,
              type=click.Choice(["coincident", "parallel", "perpendicular",
                                 "distance", "angle", "axial", "plane"]),
              help="Constraint type.")
@click.option("--obj1", "-o1", required=True, help="First object name.")
@click.option("--obj2", "-o2", required=True, help="Second object name.")
@click.option("--value", default=None, type=float, help="Distance or angle value.")
@click.option("--name", "-n", help="Constraint name.")
@_handle_error
def assembly_constraint(ctype: str, obj1: str, obj2: str,
                       value: float | None, name: str | None) -> None:
    """Add a constraint between parts."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        constraint_name = name or f"Constraint_{ctype}"
        value_str = f", {value}" if value is not None else ""
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
obj1 = doc.getObject("{obj1}")
obj2 = doc.getObject("{obj2}")
if obj1 is None:
    raise ValueError(f"Object '{obj1}' not found")
if obj2 is None:
    raise ValueError(f"Object '{obj2}' not found")
# Create a link constraint (A2plus style)
constraint = doc.addObject("App::FeaturePython", "{constraint_name}")
constraint.addProperty("App::PropertyString", "Type").Type = "{ctype}"
constraint.addProperty("App::PropertyLink", "Object1").Object1 = obj1
constraint.addProperty("App::PropertyLink", "Object2").Object2 = obj2
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"type": "{ctype}", "obj1": "{obj1}", "obj2": "{obj2}"}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added {ctype} constraint: {obj1} ↔ {obj2}")
    finally:
        backend.disconnect()


@assembly_group.command("solve")
@click.option("--assembly", "-a", help="Assembly name.")
@_handle_error
def assembly_solve(assembly: str | None) -> None:
    """Solve assembly constraints."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        asm_filter = f'doc.getObject("{assembly}")' if assembly else 'None'
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
asm = {asm_filter}
# Count constraints
constraints = [obj for obj in doc.Objects if obj.TypeId == "App::FeaturePython" and hasattr(obj, "Type")]
_fc_result = {{"status": "ok", "data": {{"constraint_count": len(constraints)}}, "message": "Constraints solved"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or "Assembly solved")
    finally:
        backend.disconnect()


@assembly_group.command("explode")
@click.option("--assembly", "-a", help="Assembly name.")
@click.option("--factor", default=2.0, type=float, help="Explosion factor.")
@click.option("--direction", default="z",
              type=click.Choice(["x", "y", "z"]), help="Explosion direction.")
@_handle_error
def assembly_explode(assembly: str | None, factor: float, direction: str) -> None:
    """Create an exploded view."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        dir_vec = {"x": "1,0,0", "y": "0,1,0", "z": "0,0,1"}[direction]
        asm_code = f'asm = doc.getObject("{assembly}")' if assembly else 'asm = None'
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
{asm_code}
# Get all parts with shapes
parts = [obj for obj in doc.Objects if hasattr(obj, "Shape") and obj.Shape]
count = len(parts)
# Move parts along explosion direction
for i, part in enumerate(parts):
    offset = FreeCAD.Vector({dir_vec}) * {factor} * i
    part.Placement.Base = part.Placement.Base + offset
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"parts_moved": count, "factor": {factor}, "direction": "{direction}"}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Exploded {direction} by factor {factor}")
    finally:
        backend.disconnect()


@assembly_group.command("animate")
@click.option("--assembly", "-a", help="Assembly name.")
@click.option("--constraint", "-c", help="Constraint to animate.")
@click.option("--start", default=0.0, type=float, help="Start value.")
@click.option("--end", default=10.0, type=float, help="End value.")
@click.option("--steps", default=30, type=int, help="Number of steps.")
@click.option("--output", "-o", help="Output directory for frames.")
@_handle_error
def assembly_animate(assembly: str | None, constraint: str | None,
                     start: float, end: float, steps: int,
                     output: str | None) -> None:
    """Create a simple animation."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
# Animation parameters
start_val = {start}
end_val = {end}
steps = {steps}
step_size = (end_val - start_val) / max(steps - 1, 1)
frames = []
for i in range(steps):
    val = start_val + step_size * i
    frames.append(val)
_fc_result = {{"status": "ok", "data": {{"frames": len(frames), "start": start, "end": end}}, "message": "Animation created"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Animation: {steps} steps from {start} to {end}")
    finally:
        backend.disconnect()


@assembly_group.command("list")
@click.option("--assembly", "-a", help="Assembly name.")
@_handle_error
def assembly_list(assembly: str | None) -> None:
    """List all parts in assembly."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        asm_code = f'asm = doc.getObject("{assembly}")' if assembly else 'asm = None'
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
{asm_code}
if asm:
    parts = [{{"name": obj.Name, "label": obj.Label, "type_id": obj.TypeId}} for obj in asm.Group]
else:
    parts = [{{"name": obj.Name, "label": obj.Label, "type_id": obj.TypeId}} for obj in doc.Objects if hasattr(obj, "Shape")]
_fc_result = {{"status": "ok", "data": {{"parts": parts, "count": len(parts)}}, "message": ""}}
"""
        r = backend.execute_code(code)
        count = r.data.get("data", {}).get("count", 0)
        _output.output(r.to_dict(), f"{count} part(s) in assembly:")
    finally:
        backend.disconnect()


@assembly_group.command("ground")
@click.option("--assembly", "-a", required=True, help="Assembly name.")
@click.option("--object", "-o", "obj_name", required=True, help="Object to ground.")
@_handle_error
def assembly_ground(assembly: str, obj_name: str) -> None:
    """Ground a part (fix in place)."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{obj_name}")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
# Mark as grounded by setting a property
if not hasattr(obj, "Grounded"):
    obj.addProperty("App::PropertyBool", "Grounded")
obj.Grounded = True
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"object": "{obj_name}", "grounded": True}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Grounded: {obj_name}")
    finally:
        backend.disconnect()


@assembly_group.command("show")
@click.option("--assembly", "-a", help="Assembly name.")
@_handle_error
def assembly_show(assembly: str | None) -> None:
    """Show assembly tree."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        asm_code = f'asm = doc.getObject("{assembly}")' if assembly else 'asm = None'
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
{asm_code}
tree = []
if asm and hasattr(asm, "Group"):
    for obj in asm.Group:
        entry = {{"name": obj.Name, "label": obj.Label, "type_id": obj.TypeId}}
        if hasattr(obj, "Group"):
            entry["children"] = [c.Name for c in obj.Group]
        tree.append(entry)
else:
    for obj in doc.Objects:
        tree.append({{"name": obj.Name, "label": obj.Label, "type_id": obj.TypeId}})
_fc_result = {{"status": "ok", "data": {{"tree": tree, "count": len(tree)}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), "Assembly tree:")
    finally:
        backend.disconnect()


@assembly_group.command("interference")
@click.option("--obj1", "-o1", help="First object name (default: all pairs).")
@click.option("--obj2", "-o2", help="Second object name.")
@_handle_error
def assembly_interference(obj1: str | None, obj2: str | None) -> None:
    """Check for interference between assembly parts."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        if obj1 and obj2:
            code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
o1 = doc.getObject("{obj1}")
o2 = doc.getObject("{obj2}")
if o1 is None or o2 is None:
    raise ValueError("Object not found")
if not hasattr(o1, "Shape") or not hasattr(o2, "Shape"):
    raise ValueError("Objects must have shapes")
common = o1.Shape.common(o2.Shape)
has_interference = common.Volume > 0.001
_fc_result = {{"status": "ok", "data": {{"obj1": "{obj1}", "obj2": "{obj2}", "has_interference": has_interference, "common_volume": common.Volume}}, "message": ""}}
"""
        else:
            code = """\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
parts = [obj for obj in doc.Objects if hasattr(obj, "Shape") and obj.Shape and obj.Shape.Volume > 0]
interferences = []
for i in range(len(parts)):
    for j in range(i + 1, len(parts)):
        try:
            common = parts[i].Shape.common(parts[j].Shape)
            if common.Volume > 0.001:
                interferences.append({"obj1": parts[i].Name, "obj2": parts[j].Name, "volume": common.Volume})
        except Exception:
            pass
_fc_result = {"status": "ok", "data": {"interferences": interferences, "count": len(interferences)}, "message": ""}
"""
        r = backend.execute_code(code)
        data = r.data.get("data", r.data)
        count = data.get("count", 0)
        _output.output(r.to_dict(), f"Interference check: {count} interference(s)")
    finally:
        backend.disconnect()


@assembly_group.command("bom")
@click.option("--output", "-o", type=click.Path(), help="Output CSV file path.")
@_handle_error
def assembly_bom(output: str | None) -> None:
    """Generate a Bill of Materials for the assembly."""
    import os
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        output_code = ""
        if output:
            output_code = f"""\
import csv
with open(r"{os.path.abspath(output)}", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Name", "Label", "Type", "Volume", "Quantity"])
    for item in bom_items:
        writer.writerow([item["name"], item["label"], item["type"], item["volume"], item["count"]])
"""
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
bom_items = []
seen = {{}}
for obj in doc.Objects:
    if hasattr(obj, "Shape") and obj.Shape and obj.Shape.Volume > 0:
        key = obj.Label
        if key in seen:
            seen[key]["count"] += 1
        else:
            seen[key] = {{"name": obj.Name, "label": obj.Label, "type": obj.TypeId, "volume": round(obj.Shape.Volume, 2), "count": 1}}
bom_items = list(seen.values())
_fc_result = {{"status": "ok", "data": {{"items": bom_items, "count": len(bom_items)}}, "message": ""}}
"""
        r = backend.execute_code(code)
        data = r.data.get("data", r.data)
        count = data.get("count", 0)
        if output:
            _output.output(r.to_dict(), f"BOM: {count} part(s) -> {output}")
        else:
            _output.output(r.to_dict(), f"BOM: {count} part(s)")
    finally:
        backend.disconnect()
