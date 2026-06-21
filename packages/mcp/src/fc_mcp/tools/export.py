"""Export MCP tools: export to various formats."""

from __future__ import annotations

import os

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
def export_step(file_path: str, backend: str = "headless") -> dict:
    """Export the current document to STEP format.

    Args:
        file_path: Output file path (.step)
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.export(file_path, "step")
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def export_stl(file_path: str, tolerance: float = 0.1, backend: str = "headless") -> dict:
    """Export the current document to STL format.

    Args:
        file_path: Output file path (.stl)
        tolerance: Mesh tessellation tolerance
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        abs_path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
shapes = [obj.Shape for obj in doc.Objects if hasattr(obj, "Shape")]
mesh = Mesh.Mesh()
for shape in shapes:
    mesh.addMesh(Mesh.Mesh(shape.tessellate({tolerance})))
mesh.write(r"{abs_path}")
"""
        r = be.execute_code(code)
        if r.status == "ok" and os.path.isfile(abs_path):
            return ToolResponse.ok("export_stl", {
                "output": abs_path,
                "format": "stl",
                "file_size": os.path.getsize(abs_path),
            }, f"Exported STL: {abs_path}").to_dict()
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def export_obj(file_path: str, backend: str = "headless") -> dict:
    """Export the current document to OBJ format.

    Args:
        file_path: Output file path (.obj)
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.export(file_path, "obj")
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def export_brep(file_path: str, backend: str = "headless") -> dict:
    """Export the current document to BREP format.

    Args:
        file_path: Output file path (.brep)
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.export(file_path, "brep")
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def export_dxf(file_path: str, backend: str = "headless") -> dict:
    """Export the current document to DXF format.

    Args:
        file_path: Output file path (.dxf)
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.export(file_path, "dxf")
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def export_svg(file_path: str, backend: str = "headless") -> dict:
    """Export the current document to SVG format.

    Args:
        file_path: Output file path (.svg)
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.export(file_path, "svg")
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def export_pdf(file_path: str, backend: str = "headless") -> dict:
    """Export the current document to PDF format via TechDraw.

    Args:
        file_path: Output file path (.pdf)
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        abs_path = os.path.abspath(file_path)
        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
page = doc.addObject("TechDraw::DrawPage", "Page")
import os
template_dir = os.path.join(FreeCAD.getResourceDir(), "Mod", "TechDraw", "Templates")
template_file = os.path.join(template_dir, "A3_Landscape_blank.svg")
if not os.path.exists(template_file):
    template_file = os.path.join(template_dir, "A4_LandscapeTD.svg")
if os.path.exists(template_file):
    page.Template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    page.Template.Template = template_file
view = doc.addObject("TechDraw::DrawViewPart", "View")
view.Source = [obj for obj in doc.Objects if hasattr(obj, "Shape") and obj.Shape]
page.addView(view)
doc.recompute()
page.exportPdf(r"{abs_path}")
"""
        r = be.execute_code(code)
        if r.status == "ok" and os.path.isfile(abs_path):
            return ToolResponse.ok("export_pdf", {
                "output": abs_path,
                "format": "pdf",
            }, f"Exported PDF: {abs_path}").to_dict()
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def export_gltf(file_path: str, backend: str = "headless") -> dict:
    """Export the current document to glTF format.

    Args:
        file_path: Output file path (.gltf)
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.export(file_path, "gltf")
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def export_3mf(file_path: str, backend: str = "headless") -> dict:
    """Export the current document to 3MF format.

    Args:
        file_path: Output file path (.3mf)
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.export(file_path, "3mf")
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def export_fcstd(file_path: str, backend: str = "headless") -> dict:
    """Save the current document as FreeCAD native .FCStd format.

    Args:
        file_path: Output file path (.FCStd)
        backend: Backend to use
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.document_save(file_path)
        return r.to_dict()
    finally:
        be.disconnect()
