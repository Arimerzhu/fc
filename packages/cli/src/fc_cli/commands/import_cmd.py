"""Import commands.

Import CAD/mesh files into the current document.
Supported formats: STEP, IGES, STL, OBJ, DXF, SVG, BREP, 3MF, PLY, OFF, glTF.
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


def _validate_import_path(path: str) -> str | None:
    """Validate import file path for security. Returns None on failure."""
    from fc_cli.main import _output
    from fc_core.security import SecurityError, validate_import_path
    try:
        return validate_import_path(path)
    except SecurityError as e:
        _output.error(str(e), code=e.code, suggestion=e.suggestion)
        return None
    except FileNotFoundError as e:
        _output.error(str(e), code="FILE_NOT_FOUND",
                      suggestion="Check the file path exists")
        return None


def _import_file(backend, file_path: str) -> None:
    """Generic import function."""
    from fc_cli.main import _output
    abs_path = os.path.abspath(file_path)

    format_handlers = {
        "step": lambda: backend.execute_code(f'import Part\nPart.insert(r"{abs_path}", FreeCAD.ActiveDocument.Name)'),
        "iges": lambda: backend.execute_code(f'import Part\nPart.insert(r"{abs_path}", FreeCAD.ActiveDocument.Name)'),
        "stl": lambda: backend.execute_code(f'import Mesh\nMesh.insert(r"{abs_path}")'),
        "obj": lambda: backend.execute_code(f'import Mesh\nMesh.insert(r"{abs_path}")'),
        "brep": lambda: backend.execute_code(f'import Part\nshape = Part.Shape()\nshape.read(r"{abs_path}")\nobj = FreeCAD.ActiveDocument.addObject("Part::Feature", "Imported")\nobj.Shape = shape\nFreeCAD.ActiveDocument.recompute()'),
        "dxf": lambda: backend.execute_code(f'import importDXF\nimportDXF.insert(r"{abs_path}")'),
        "svg": lambda: backend.execute_code(f'import importSVG\nimportSVG.insert(r"{abs_path}")'),
        "3mf": lambda: backend.execute_code(f'import Mesh\nMesh.insert(r"{abs_path}")'),
        "ply": lambda: backend.execute_code(f'import Mesh\nMesh.insert(r"{abs_path}")'),
        "off": lambda: backend.execute_code(f'import Mesh\nMesh.insert(r"{abs_path}")'),
        "gltf": lambda: backend.execute_code(f'import Mesh\nMesh.insert(r"{abs_path}")'),
    }

    # Detect format from extension
    ext = os.path.splitext(abs_path)[1].lstrip(".").lower()

    handler = format_handlers.get(ext.lower())
    if handler is None:
        # Try auto-detect
        handler = format_handlers.get("step")

    r = handler()
    _output.output(r.to_dict(), r.message or f"Imported: {file_path}")


@click.group("import")
def import_group():
    """Import commands for various file formats."""
    pass


@import_group.command("auto")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_auto(path: str) -> None:
    """Auto-detect format and import."""
    from fc_cli.main import _output
    validated = _validate_import_path(path)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        _import_file(backend, validated)
    finally:
        backend.disconnect()


@import_group.command("step")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_step(path: str) -> None:
    """Import a STEP file."""
    validated = _validate_import_path(path)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        _import_file(backend, validated)
    finally:
        backend.disconnect()


@import_group.command("stl")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_stl(path: str) -> None:
    """Import an STL mesh file."""
    validated = _validate_import_path(path)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        _import_file(backend, validated)
    finally:
        backend.disconnect()


@import_group.command("obj")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_obj(path: str) -> None:
    """Import an OBJ mesh file."""
    validated = _validate_import_path(path)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        _import_file(backend, validated)
    finally:
        backend.disconnect()


@import_group.command("dxf")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_dxf(path: str) -> None:
    """Import a DXF file."""
    validated = _validate_import_path(path)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        _import_file(backend, validated)
    finally:
        backend.disconnect()


@import_group.command("brep")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_brep(path: str) -> None:
    """Import a BREP file."""
    validated = _validate_import_path(path)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        _import_file(backend, validated)
    finally:
        backend.disconnect()


@import_group.command("info")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_info(path: str) -> None:
    """Get information about an importable file without importing."""
    from fc_cli.main import _output
    from fc_core.security import SecurityError, validate_path
    try:
        abs_path = validate_path(path, must_exist=True)
    except (SecurityError, FileNotFoundError) as e:
        _output.error(str(e), code=getattr(e, 'code', 'FILE_NOT_FOUND'))
        return

    ext = os.path.splitext(abs_path)[1].lstrip(".").lower()
    size = os.path.getsize(abs_path)

    info = {
        "file": abs_path,
        "format": ext,
        "size_bytes": size,
        "size_human": f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB",
    }

    # Try to get mesh info for mesh formats
    if ext in ("stl", "obj", "ply", "off"):
        backend = _get_backend()
        try:
            backend.connect()
            code = f"""\
import Mesh
mesh = Mesh.Mesh()
mesh.read(r"{abs_path}")
_fc_result = {{
    "status": "ok",
    "data": {{
        "file": r"{abs_path}",
        "format": "{ext}",
        "size_bytes": {size},
        "count_points": mesh.CountPoints,
        "count_edges": mesh.CountEdges,
        "count_facets": mesh.CountFacets,
        "bounding_box": {{
            "x": [mesh.BoundBox.XMin, mesh.BoundBox.XMax],
            "y": [mesh.BoundBox.YMin, mesh.BoundBox.YMax],
            "z": [mesh.BoundBox.ZMin, mesh.BoundBox.ZMax],
        }},
        "is_solid": mesh.isSolid(),
    }},
    "message": ""
}}
"""
            r = backend.execute_code(code)
            if r.status == "ok":
                info.update(r.data)
        finally:
            backend.disconnect()

    _output.output(info, f"File info: {abs_path}")


@import_group.command("iges")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_iges(path: str) -> None:
    """Import an IGES file."""
    validated = _validate_import_path(path)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        _import_file(backend, validated)
    finally:
        backend.disconnect()


@import_group.command("svg")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_svg_cmd(path: str) -> None:
    """Import an SVG file."""
    validated = _validate_import_path(path)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        _import_file(backend, validated)
    finally:
        backend.disconnect()


@import_group.command("3mf")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_3mf(path: str) -> None:
    """Import a 3MF file."""
    validated = _validate_import_path(path)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        _import_file(backend, validated)
    finally:
        backend.disconnect()


@import_group.command("ply")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_ply(path: str) -> None:
    """Import a PLY mesh file."""
    validated = _validate_import_path(path)
    if validated is None:
        return
    backend = _get_backend()
    try:
        backend.connect()
        _import_file(backend, validated)
    finally:
        backend.disconnect()
