"""Material commands.

Commands for material management:
  material list        — List available materials
  material show        — Show material properties
  material assign      — Assign material to an object
  material create      — Create a custom material
  material edit        — Edit material properties
  material remove      — Remove a material
  material library     — List material libraries
  material export      — Export material card
  material import      — Import material card
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


@click.group("material")
def material_group():
    """Material management commands."""
    pass


@material_group.command("list")
@click.option("--library", "-l", default=None, help="Filter by library name.")
@_handle_error
def material_list(library: str | None) -> None:
    """List available materials in the current document."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = """\
import FreeCAD
doc = FreeCAD.ActiveDocument
if doc is None:
    _fc_result = {"status": "error", "data": {}, "message": "No active document"}
else:
    materials = []
    for obj in doc.Objects:
        if "Material" in obj.TypeId:
            mat_data = {"name": obj.Name, "label": obj.Label, "type": obj.TypeId}
            if hasattr(obj, "Material") and isinstance(obj.Material, dict):
                mat_data["properties"] = obj.Material
            materials.append(mat_data)
    _fc_result = {"status": "ok", "data": {"materials": materials, "count": len(materials)}, "message": ""}
"""
        if library:
            code = code.replace(
                '"count": len(materials)}',
                f'"count": len(materials), "library_filter": "{library}"}}'
            )
        r = backend.execute_code(code)
        if r.status == "ok":
            mats = r.data.get("materials", [])
            _output.output(r.to_dict(), f"{len(mats)} material(s):")
        else:
            _output.output(r.to_dict())
    finally:
        backend.disconnect()


@material_group.command("show")
@click.argument("name")
@_handle_error
def material_show(name: str) -> None:
    """Show material properties.

    NAME is the material name or path (e.g. "Materials/Steel").
    """
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
if doc is None:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No active document"}}
else:
    obj = doc.getObject("{name}")
    if obj is None:
        _fc_result = {{"status": "error", "data": {{}}, "message": "Material '{name}' not found"}}
    elif "Material" not in obj.TypeId:
        _fc_result = {{"status": "error", "data": {{}}, "message": f"Object '{name}' is not a material (TypeId: {{obj.TypeId}})"}}
    else:
        mat = {{"name": obj.Name, "label": obj.Label, "type": obj.TypeId}}
        if hasattr(obj, "Material") and isinstance(obj.Material, dict):
            mat["properties"] = obj.Material
        _fc_result = {{"status": "ok", "data": mat, "message": ""}}
"""
        r = backend.execute_code(code)
        if r.status == "ok":
            _output.output(r.to_dict(), f"Material '{name}':")
        else:
            _output.output(r.to_dict())
    finally:
        backend.disconnect()


@material_group.command("assign")
@click.option("--object", "-o", "obj_name", required=True, help="Object name to assign material to.")
@click.option("--material", "-m", required=True, help="Material name to assign.")
@_handle_error
def material_assign(obj_name: str, material: str) -> None:
    """Assign a material to an object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
if doc is None:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No active document"}}
else:
    target = doc.getObject("{obj_name}")
    if target is None:
        _fc_result = {{"status": "error", "data": {{}}, "message": "Object '{obj_name}' not found"}}
    else:
        mat = doc.getObject("{material}")
        if mat is None:
            _fc_result = {{"status": "error", "data": {{}}, "message": "Material '{material}' not found"}}
        elif "Material" not in mat.TypeId:
            _fc_result = {{"status": "error", "data": {{}}, "message": f"Object '{material}' is not a material"}}
        else:
            target.Material = mat.Name
            doc.recompute()
            _fc_result = {{"status": "ok", "data": {{"object": "{obj_name}", "material": "{material}"}}, "message": "Material assigned"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Assigned '{material}' to '{obj_name}'")
    finally:
        backend.disconnect()


@material_group.command("create")
@click.option("--name", "-n", required=True, help="Material name.")
@click.option("--density", default=None, type=float, help="Density in kg/m³.")
@click.option("--youngs-modulus", default=None, type=float, help="Young's modulus in Pa.")
@click.option("--poisson-ratio", default=None, type=float, help="Poisson ratio.")
@click.option("--tensile-strength", default=None, type=float, help="Tensile strength in Pa.")
@click.option("--color", default=None, help="Color as r,g,b (0-1).")
@_handle_error
def material_create(name: str, density: float | None, youngs_modulus: float | None,
                    poisson_ratio: float | None, tensile_strength: float | None,
                    color: str | None) -> None:
    """Create a custom material."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        props = []
        if density is not None:
            props.append(f'"Density": "{density} kg/m^3"')
        if youngs_modulus is not None:
            props.append(f'"YoungsModulus": "{youngs_modulus} Pa"')
        if poisson_ratio is not None:
            props.append(f'"PoissonsRatio": "{poisson_ratio}"')
        if tensile_strength is not None:
            props.append(f'"TensileStrength": "{tensile_strength} Pa"')
        if color is not None:
            props.append(f'"Color": "{color}"')
        props_str = ", ".join(props)
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
if doc is None:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No active document"}}
else:
    mat = doc.addObject("App::MaterialObjectPython", "Material")
    mat.Material = {{"Name": "{name}"{", " + props_str if props_str else ""}}}
    doc.recompute()
    _fc_result = {{"status": "ok", "data": {{"name": "{name}", "object": mat.Name}}, "message": "Material created"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created material: {name}")
    finally:
        backend.disconnect()


@material_group.command("edit")
@click.argument("name")
@click.option("--property", "-p", multiple=True, help="Property as key=value (can repeat).")
@click.option("--value", default=None, help="Value for the property (used with single --property).")
@_handle_error
def material_edit(name: str, property: tuple, value: str | None) -> None:
    """Edit material properties.

    NAME is the material name to edit.
    """
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        props = {}
        for p in property:
            if "=" not in p:
                _output.error(f"Property must be key=value, got: {p}",
                              code="INVALID_PROPERTY")
                return
            k, v = p.split("=", 1)
            props[k.strip()] = v.strip()
        if value is not None and not props:
            _output.error("Use --property KEY=VALUE or --property KEY --value VALUE",
                          code="INVALID_PROPERTY")
            return
        props_str = ", ".join(f'"{k}": "{v}"' for k, v in props.items())
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
if doc is None:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No active document"}}
else:
    mat = doc.getObject("{name}")
    if mat is None:
        _fc_result = {{"status": "error", "data": {{}}, "message": "Material '{name}' not found"}}
    elif "Material" not in mat.TypeId:
        _fc_result = {{"status": "error", "data": {{}}, "message": f"Object '{name}' is not a material"}}
    else:
        if not hasattr(mat, "Material") or not isinstance(mat.Material, dict):
            mat.Material = {{}}
        mat.Material.update({{{props_str}}})
        doc.recompute()
        _fc_result = {{"status": "ok", "data": {{"name": "{name}", "updated": {list(props.keys())}}}, "message": "Material updated"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Updated material: {name}")
    finally:
        backend.disconnect()


@material_group.command("remove")
@click.argument("name")
@_handle_error
def material_remove(name: str) -> None:
    """Remove a material from the document.

    NAME is the material name to remove.
    """
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
if doc is None:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No active document"}}
else:
    mat = doc.getObject("{name}")
    if mat is None:
        _fc_result = {{"status": "error", "data": {{}}, "message": "Material '{name}' not found"}}
    elif "Material" not in mat.TypeId:
        _fc_result = {{"status": "error", "data": {{}}, "message": f"Object '{name}' is not a material"}}
    else:
        doc.removeObject("{name}")
        doc.recompute()
        _fc_result = {{"status": "ok", "data": {{"name": "{name}"}}, "message": "Material removed"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Removed material: {name}")
    finally:
        backend.disconnect()


@material_group.command("library")
@_handle_error
def material_library() -> None:
    """List available material libraries."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = """\
import FreeCAD
import os
material_dirs = []
# Check standard FreeCAD material directories
fc_dir = FreeCAD.getResourceDir()
mat_dir = os.path.join(fc_dir, "Mod", "Material")
if os.path.isdir(mat_dir):
    material_dirs.append(mat_dir)
# Also check user home directory
home_mat = os.path.join(os.path.expanduser("~"), ".FreeCAD", "Material")
if os.path.isdir(home_mat):
    material_dirs.append(home_mat)
# Scan for .FCMat files
libraries = []
for d in material_dirs:
    libs = []
    for f in os.listdir(d):
        if f.endswith(".FCMat"):
            libs.append(f)
    libraries.append({"path": d, "materials": sorted(libs), "count": len(libs)})
_fc_result = {"status": "ok", "data": {"libraries": libraries, "total_dirs": len(libraries)}, "message": ""}
"""
        r = backend.execute_code(code)
        if r.status == "ok":
            libs = r.data.get("libraries", [])
            total = sum(l.get("count", 0) for l in libs)
            _output.output(r.to_dict(), f"{total} material(s) in {len(libs)} directorie(s):")
        else:
            _output.output(r.to_dict())
    finally:
        backend.disconnect()


@material_group.command("export")
@click.argument("name")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output file path.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def material_export(name: str, output: str, overwrite: bool) -> None:
    """Export a material card to a file.

    NAME is the material name to export.
    """
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
import json
doc = FreeCAD.ActiveDocument
if doc is None:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No active document"}}
else:
    mat = doc.getObject("{name}")
    if mat is None:
        _fc_result = {{"status": "error", "data": {{}}, "message": "Material '{name}' not found"}}
    elif "Material" not in mat.TypeId:
        _fc_result = {{"status": "error", "data": {{}}, "message": f"Object '{name}' is not a material"}}
    else:
        mat_data = {{"name": mat.Name, "label": mat.Label, "type": mat.TypeId}}
        if hasattr(mat, "Material") and isinstance(mat.Material, dict):
            mat_data["properties"] = mat.Material
        output_path = r"{os.path.abspath(output)}"
        with open(output_path, "w") as f:
            json.dump(mat_data, f, indent=2)
        _fc_result = {{"status": "ok", "data": {{"output": output_path, "name": "{name}"}}, "message": "Material exported"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Exported material: {name} -> {output}")
    finally:
        backend.disconnect()


@material_group.command("import")
@click.argument("path", type=click.Path(exists=True))
@click.option("--name", "-n", default=None, help="Override material name.")
@_handle_error
def material_import(path: str, name: str | None) -> None:
    """Import a material card from a file.

    PATH is the file path to import (.FCMat or .json).
    """
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        abs_path = os.path.abspath(path)
        name_override = f'"{name}"' if name else "None"
        code = f"""\
import FreeCAD
import json
import os
doc = FreeCAD.ActiveDocument
if doc is None:
    _fc_result = {{"status": "error", "data": {{}}, "message": "No active document"}}
else:
    file_path = r"{abs_path}"
    if not os.path.exists(file_path):
        _fc_result = {{"status": "error", "data": {{}}, "message": f"File not found: {{file_path}}"}}
    elif file_path.endswith(".FCMat"):
        # FCMat is a FreeCAD material file - read its contents
        mat_name = "{name or ""}" or os.path.splitext(os.path.basename(file_path))[0]
        mat = doc.addObject("App::MaterialObjectPython", "Material")
        mat.Material = {{"Name": mat_name}}
        with open(file_path, "r") as f:
            content = f.read()
        mat.Material["Description"] = content[:200]
        doc.recompute()
        _fc_result = {{"status": "ok", "data": {{"name": mat_name, "object": mat.Name, "source": file_path}}, "message": "Material imported"}}
    elif file_path.endswith(".json"):
        with open(file_path, "r") as f:
            mat_data = json.load(f)
        mat_name = "{name or ""}" or mat_data.get("name", "ImportedMaterial")
        mat = doc.addObject("App::MaterialObjectPython", "Material")
        if "properties" in mat_data and isinstance(mat_data["properties"], dict):
            mat.Material = mat_data["properties"]
        else:
            mat.Material = mat_data
        mat.Material["Name"] = mat_name
        doc.recompute()
        _fc_result = {{"status": "ok", "data": {{"name": mat_name, "object": mat.Name, "source": file_path}}, "message": "Material imported"}}
    else:
        _fc_result = {{"status": "error", "data": {{}}, "message": "Unsupported file format. Use .FCMat or .json"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Imported material from: {path}")
    finally:
        backend.disconnect()
