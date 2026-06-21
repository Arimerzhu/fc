"""Import utilities with auto-detection.

Provides high-level import functions that auto-detect file format
from extension and content, with support for all major CAD/mesh formats.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fc_core.backend import HeadlessBackend
from fc_core.types import ToolResponse


# ── Format Detection ──

MESH_EXTENSIONS = {".stl", ".obj", ".ply", ".off", ".3mf"}
CAD_EXTENSIONS = {".step", ".stp", ".iges", ".igs", ".brep", ".fcstd", ".fcstd1"}
DRAFT_EXTENSIONS = {".dxf", ".svg"}
ALL_EXTENSIONS = MESH_EXTENSIONS | CAD_EXTENSIONS | DRAFT_EXTENSIONS

IMPORT_METHODS: dict[str, str] = {
    ".stl": "mesh",
    ".obj": "mesh",
    ".ply": "mesh",
    ".off": "mesh",
    ".3mf": "mesh",
    ".step": "cad",
    ".stp": "cad",
    ".iges": "cad",
    ".igs": "cad",
    ".brep": "cad",
    ".fcstd": "freecad",
    ".fcstd1": "freecad",
    ".dxf": "draft",
    ".svg": "draft",
}


def detect_format(file_path: str) -> str:
    """Detect import format from file extension.

    Returns:
        Format category: 'mesh', 'cad', 'draft', 'freecad', or 'unknown'.
    """
    ext = Path(file_path).suffix.lower()
    return IMPORT_METHODS.get(ext, "unknown")


def get_import_info(file_path: str) -> dict[str, Any]:
    """Get information about a file before importing.

    Returns:
        Dict with format, method, file size, and extension info.
    """
    ext = Path(file_path).suffix.lower()
    fmt = detect_format(file_path)
    info = {
        "path": file_path,
        "extension": ext,
        "format": fmt,
        "method": IMPORT_METHODS.get(ext, "unknown"),
        "exists": os.path.isfile(file_path),
    }
    if info["exists"]:
        info["file_size"] = os.path.getsize(file_path)
    return info


def import_file(
    backend: HeadlessBackend,
    file_path: str,
    merge: bool = False,
) -> ToolResponse:
    """Import a file with auto-detected format.

    Args:
        backend: Connected backend instance.
        file_path: Path to the file to import.
        merge: If True, merge into current document. If False, open as new.

    Returns:
        ToolResponse with import result.
    """
    if not os.path.isfile(file_path):
        return ToolResponse.error(
            "import",
            "FILE_NOT_FOUND",
            f"File not found: {file_path}",
        )

    abs_path = os.path.abspath(file_path)
    ext = Path(file_path).suffix.lower()
    fmt = detect_format(file_path)

    if fmt == "freecad":
        # Open FCStd directly
        if merge:
            return _import_fcstd_merge(backend, abs_path)
        return backend.document_open(abs_path)

    if fmt == "mesh":
        return _import_mesh(backend, abs_path, ext)

    if fmt == "cad":
        return _import_cad(backend, abs_path, ext)

    if fmt == "draft":
        return _import_draft(backend, abs_path, ext)

    return ToolResponse.error(
        "import",
        "UNKNOWN_FORMAT",
        f"Cannot import file with extension: {ext}",
        suggestion=f"Supported: {', '.join(sorted(ALL_EXTENSIONS))}",
    )


def _import_mesh(backend: HeadlessBackend, path: str, ext: str) -> ToolResponse:
    """Import a mesh file."""
    code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
mesh = Mesh.Mesh(r"{path}")
mesh_obj = doc.addObject("Mesh::Feature", "ImportedMesh")
mesh_obj.Mesh = mesh
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": mesh_obj.Name, "type": "mesh"}}, "message": ""}}
"""
    r = backend.execute_code(code)
    if r.status == "ok":
        return ToolResponse.ok("import", r.data, f"Imported mesh: {path}")
    return ToolResponse.error("import", "IMPORT_FAILED", r.message)


def _import_cad(backend: HeadlessBackend, path: str, ext: str) -> ToolResponse:
    """Import a CAD file (STEP, IGES, BREP)."""
    code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
shape = Part.Shape()
shape.read(r"{path}")
obj = doc.addObject("Part::Feature", "ImportedPart")
obj.Shape = shape
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": obj.Name, "type": "cad"}}, "message": ""}}
"""
    r = backend.execute_code(code)
    if r.status == "ok":
        return ToolResponse.ok("import", r.data, f"Imported CAD: {path}")
    return ToolResponse.error("import", "IMPORT_FAILED", r.message)


def _import_draft(backend: HeadlessBackend, path: str, ext: str) -> ToolResponse:
    """Import a DXF or SVG file."""
    if ext == ".dxf":
        importer = "importDXF"
    else:
        importer = "importSVG"
    code = f"""\
import FreeCAD
import {importer}
doc = FreeCAD.ActiveDocument
importer.open(r"{path}")
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"format": "{ext}", "method": "{importer}"}}, "message": ""}}
"""
    r = backend.execute_code(code)
    if r.status == "ok":
        return ToolResponse.ok("import", r.data, f"Imported {ext}: {path}")
    return ToolResponse.error("import", "IMPORT_FAILED", r.message)


def _import_fcstd_merge(backend: HeadlessBackend, path: str) -> ToolResponse:
    """Merge an FCStd file into the current document."""
    code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
# Open the source document in a temporary context
src_doc = FreeCAD.open(r"{path}")
# Copy all objects
count = 0
for obj in src_doc.Objects:
    # Create a copy in the active document
    if hasattr(obj, "Shape"):
        new_obj = doc.addObject("Part::Feature", obj.Name)
        new_obj.Shape = obj.Shape.copy()
        count += 1
FreeCAD.closeDocument(src_doc.Name)
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"objects_copied": count}}, "message": ""}}
"""
    r = backend.execute_code(code)
    if r.status == "ok":
        copied = r.data.get("objects_copied", 0)
        return ToolResponse.ok("import", r.data, f"Merged {copied} objects from {path}")
    return ToolResponse.error("import", "IMPORT_FAILED", r.message)


def list_supported_formats() -> dict[str, list[str]]:
    """List all supported import formats by category."""
    return {
        "mesh": sorted(MESH_EXTENSIONS),
        "cad": sorted(CAD_EXTENSIONS - {".fcstd", ".fcstd1"}),
        "freecad": [".fcstd", ".fcstd1"],
        "draft": sorted(DRAFT_EXTENSIONS),
    }
