"""Export commands.

Export the current document or selected objects to various file formats.
Supported formats: STEP, IGES, STL, OBJ, BREP, DXF, DWG, SVG, glTF, 3MF, PLY, OFF, AMF, PDF, FCSTD.
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


def _validate_output_path(output: str, overwrite: bool) -> str | None:
    """Validate export output path for security. Returns None on failure."""
    from fc_cli.main import _output
    from fc_core.security import SecurityError, validate_export_path
    try:
        return validate_export_path(output, overwrite=overwrite)
    except SecurityError as e:
        _output.error(str(e), code=e.code, suggestion=e.suggestion)
        return None


@click.group("export")
def export_group():
    """Export commands for various file formats."""
    pass


def _do_export(output: str, fmt: str, overwrite: bool, verify: bool = True) -> None:
    """共享导出逻辑，包含路径验证和几何验证。"""
    from fc_cli.main import _output
    validated = _validate_output_path(output, overwrite)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.export(validated, fmt, verify=verify)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@export_group.command("step")
@click.argument("output", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@click.option("--verify/--no-verify", default=True, help="验证导出文件的几何正确性（默认开启）。")
@_handle_error
def export_step(output: str, overwrite: bool, verify: bool) -> None:
    """Export to STEP format."""
    _do_export(output, "step", overwrite, verify)


@export_group.command("stl")
@click.argument("output", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@click.option("--tolerance", default=0.1, type=float, help="Mesh tessellation tolerance.")
@click.option("--verify/--no-verify", default=True, help="验证导出文件的几何正确性（默认开启）。")
@_handle_error
def export_stl(output: str, overwrite: bool, tolerance: float, verify: bool) -> None:
    """Export to STL format."""
    _do_export(output, "stl", overwrite, verify)


@export_group.command("obj")
@click.argument("output", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@click.option("--verify/--no-verify", default=True, help="验证导出文件的几何正确性（默认开启）。")
@_handle_error
def export_obj(output: str, overwrite: bool, verify: bool) -> None:
    """Export to OBJ format."""
    _do_export(output, "obj", overwrite, verify)


@export_group.command("brep")
@click.argument("output", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@click.option("--verify/--no-verify", default=True, help="验证导出文件的几何正确性（默认开启）。")
@_handle_error
def export_brep(output: str, overwrite: bool, verify: bool) -> None:
    """Export to BREP format."""
    _do_export(output, "brep", overwrite, verify)


@export_group.command("dxf")
@click.argument("output", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def export_dxf(output: str, overwrite: bool) -> None:
    """Export to DXF format."""
    _do_export(output, "dxf", overwrite)


@export_group.command("dwg")
@click.argument("output", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@click.option("--version", default="R2018",
              type=click.Choice(["R12", "R13", "R14", "R2000", "R2004", "R2007", "R2010", "R2013", "R2018"]),
              help="DWG version (default: R2018).")
@_handle_error
def export_dwg(output: str, overwrite: bool, version: str) -> None:
    """Export to DWG format (via ODA File Converter).

    Requires ODA File Converter to be installed.
    The document is first exported to DXF, then converted to DWG.
    """
    from fc_cli.main import _output
    validated = _validate_output_path(output, overwrite)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.export_dwg(validated, version=version)
        if r.status == "ok":
            _output.output(r.to_dict(), r.message)
        else:
            _output.error(r.message, code=r.error_code, suggestion=r.suggestion)
    finally:
        backend.disconnect()


@export_group.command("svg")
@click.argument("output", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def export_svg(output: str, overwrite: bool) -> None:
    """Export to SVG format."""
    _do_export(output, "svg", overwrite)


@export_group.command("pdf")
@click.argument("output", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def export_pdf(output: str, overwrite: bool) -> None:
    """Export to PDF format."""
    from fc_cli.main import _output
    validated = _validate_output_path(output, overwrite)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        # PDF export via TechDraw page
        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
# Create a page with an A3 template
page = doc.addObject("TechDraw::DrawPage", "Page")
# Try to find a template
import os
template_dir = os.path.join(FreeCAD.getResourceDir(), "Mod", "TechDraw", "Templates")
template_file = os.path.join(template_dir, "A3_Landscape_blank.svg")
if not os.path.exists(template_file):
    template_file = os.path.join(template_dir, "A4_LandscapeTD.svg")
if os.path.exists(template_file):
    page.Template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    page.Template.Template = template_file
# Add a view of all objects
view = doc.addObject("TechDraw::DrawViewPart", "View")
view.Source = [obj for obj in doc.Objects if hasattr(obj, "Shape") and obj.Shape]
page.addView(view)
doc.recompute()
page.exportPdf(r"{validated}")
"""
        r = backend.execute_code(code)
        if r.status == "ok" and os.path.isfile(validated):
            _output.output(r.to_dict(), f"Exported PDF: {validated}")
        else:
            _output.error("PDF export failed", code="EXPORT_FAILED",
                          message=r.message)
    finally:
        backend.disconnect()


@export_group.command("gltf")
@click.argument("output", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def export_gltf(output: str, overwrite: bool) -> None:
    """Export to glTF format."""
    _do_export(output, "gltf", overwrite)


@export_group.command("3mf")
@click.argument("output", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def export_3mf(output: str, overwrite: bool) -> None:
    """Export to 3MF format."""
    _do_export(output, "3mf", overwrite)


@export_group.command("fcstd")
@click.argument("output", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@click.option("--verify/--no-verify", default=True, help="验证导出文件的几何正确性（默认开启）。")
@_handle_error
def export_fcstd(output: str, overwrite: bool, verify: bool) -> None:
    """Save as FreeCAD native .FCStd format."""
    from fc_cli.main import _output
    validated = _validate_output_path(output, overwrite)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.document_save(validated)
        if verify and r.status == "ok" and os.path.isfile(validated):
            # FCStd 保存后验证
            from fc_core.verify import CADVerifier
            verifier = CADVerifier()
            report = verifier.verify(validated, fmt="fcstd")
            data = r.to_dict()
            if not report.passed:
                failed_msgs = [c.message for c in report.checks if not c.passed]
                _output.error(
                    f"保存成功但验证失败: {'; '.join(failed_msgs)}",
                    code="VERIFICATION_FAILED",
                )
                return
            data.setdefault("data", {})["verification"] = report.to_dict()
            _output.output(data, r.message)
        else:
            _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@export_group.command("presets")
@_handle_error
def export_presets() -> None:
    """List available export format presets."""
    from fc_cli.main import _output
    presets = {
        "step": {"ext": ".step", "description": "ISO 10303 AP214/AP242"},
        "iges": {"ext": ".iges", "description": "IGES 5.3"},
        "stl": {"ext": ".stl", "description": "Stereolithography (binary)"},
        "stl_fine": {"ext": ".stl", "description": "STL with fine tessellation"},
        "obj": {"ext": ".obj", "description": "Wavefront OBJ"},
        "brep": {"ext": ".brep", "description": "OpenCASCADE BREP"},
        "dxf": {"ext": ".dxf", "description": "AutoCAD DXF"},
        "svg": {"ext": ".svg", "description": "Scalable Vector Graphics"},
        "gltf": {"ext": ".gltf", "description": "GL Transmission Format"},
        "3mf": {"ext": ".3mf", "description": "3D Manufacturing Format"},
        "ply": {"ext": ".ply", "description": "Stanford PLY"},
        "off": {"ext": ".off", "description": "Object File Format"},
        "amf": {"ext": ".amf", "description": "Additive Manufacturing Format"},
        "pdf": {"ext": ".pdf", "description": "Portable Document Format"},
        "fcstd": {"ext": ".FCStd", "description": "FreeCAD native format"},
        "dwg": {"ext": ".dwg", "description": "AutoCAD DWG (via ODA File Converter)"},
        "png": {"ext": ".png", "description": "Screenshot (PNG)"},
        "jpg": {"ext": ".jpg", "description": "Screenshot (JPEG)"},
    }
    _output.output(presets, "Available export presets:")


@export_group.command("iges")
@click.argument("output", type=click.Path())
@click.option("--objects", "-o", help="Object names (comma-sep, default: all).")
@_handle_error
def export_iges(output: str, objects: str | None) -> None:
    """Export to IGES format."""
    from fc_cli.main import _output
    from fc_core.security import SecurityError, validate_path
    try:
        abs_path = validate_path(output, must_exist=False)
    except SecurityError as e:
        _output.error(str(e), code=e.code, suggestion=e.suggestion)
        return
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    backend = _get_backend()
    try:
        backend.connect()
        if objects:
            obj_list = ", ".join(f'doc.getObject("{o.strip()}")' for o in objects.split(","))
            code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
objs = [{obj_list}]
objs = [o for o in objs if o is not None]
Part.export(objs, r"{abs_path}")
"""
        else:
            code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
Part.export(doc.Objects, r"{abs_path}")
"""
        r = backend.execute_code(code)
        if r.status == "ok" and os.path.isfile(abs_path):
            file_size = os.path.getsize(abs_path)
            _output.output(r.to_dict(), f"Exported IGES: {abs_path} ({file_size} bytes)")
        else:
            _output.error("IGES export failed", code="EXPORT_FAILED")
    finally:
        backend.disconnect()


@export_group.command("off")
@click.argument("output", type=click.Path())
@_handle_error
def export_off(output: str) -> None:
    """Export to OFF format."""
    from fc_cli.main import _output
    from fc_core.security import SecurityError, validate_path
    try:
        abs_path = validate_path(output, must_exist=False)
    except SecurityError as e:
        _output.error(str(e), code=e.code, suggestion=e.suggestion)
        return
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
shapes = [obj.Shape for obj in doc.Objects if hasattr(obj, "Shape") and obj.Shape]
mesh = Mesh.Mesh()
for shape in shapes:
    mesh.addMesh(Mesh.Mesh(shape.tessellate(0.1)))
mesh.write(r"{abs_path}")
"""
        r = backend.execute_code(code)
        if r.status == "ok" and os.path.isfile(abs_path):
            _output.output(r.to_dict(), f"Exported OFF: {abs_path}")
        else:
            _output.error("OFF export failed", code="EXPORT_FAILED")
    finally:
        backend.disconnect()


@export_group.command("ply")
@click.argument("output", type=click.Path())
@_handle_error
def export_ply(output: str) -> None:
    """Export to PLY format."""
    from fc_cli.main import _output
    from fc_core.security import SecurityError, validate_path
    try:
        abs_path = validate_path(output, must_exist=False)
    except SecurityError as e:
        _output.error(str(e), code=e.code, suggestion=e.suggestion)
        return
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
shapes = [obj.Shape for obj in doc.Objects if hasattr(obj, "Shape") and obj.Shape]
mesh = Mesh.Mesh()
for shape in shapes:
    mesh.addMesh(Mesh.Mesh(shape.tessellate(0.1)))
mesh.write(r"{abs_path}")
"""
        r = backend.execute_code(code)
        if r.status == "ok" and os.path.isfile(abs_path):
            _output.output(r.to_dict(), f"Exported PLY: {abs_path}")
        else:
            _output.error("PLY export failed", code="EXPORT_FAILED")
    finally:
        backend.disconnect()
