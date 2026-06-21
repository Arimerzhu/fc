"""TechDraw commands.

Commands for TechDraw workbench operations:
  techdraw page       — Create a new drawing page
  techdraw view       — Add a view to a page
  techdraw dimension  — Add a dimension to a view
  techdraw annotation — Add annotation text
  techdraw symbol     — Add a symbol
  techdraw export     — Export page to SVG/PDF
  techdraw list       — List all pages
  techdraw get        — Get page details
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


@click.group("techdraw")
def techdraw_group():
    """TechDraw drawing commands."""
    pass


@techdraw_group.command("page")
@click.option("--name", "-n", default="Page", help="Page name.")
@click.option("--template", "-t", help="Template file path.")
@click.option("--format", default="A3",
              type=click.Choice(["A4", "A3", "A2", "A1", "A0"]),
              help="Page format.")
@_handle_error
def techdraw_page(name: str, template: str | None, format: str) -> None:
    """Create a new TechDraw drawing page."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        if template:
            template_path = os.path.abspath(template)
            code = f"""\
import FreeCAD
import TechDraw
import os
doc = FreeCAD.ActiveDocument
page = doc.addObject("TechDraw::DrawPage", "{name}")
page.Template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
page.Template.Template = r"{template_path}"
doc.recompute()
"""
        else:
            template_dir = "${FREECAD_TEMPLATE_DIR}"
            code = f"""\
import FreeCAD
import TechDraw
import os
doc = FreeCAD.ActiveDocument
page = doc.addObject("TechDraw::DrawPage", "{name}")
# Try to find a template for {format}
template_dir = os.path.join(FreeCAD.getResourceDir(), "Mod", "TechDraw", "Templates")
template_candidates = [
    "{format}_Landscape_blank.svg",
    "{format}_LandscapeTD.svg",
    "{format}_PortraitTD.svg",
    "{format}_blank.svg",
]
template_file = None
for candidate in template_candidates:
    path = os.path.join(template_dir, candidate)
    if os.path.exists(path):
        template_file = path
        break
if template_file is None:
    # Fallback: try A4 templates
    for candidate in ["A4_LandscapeTD.svg", "A4_PortraitTD.svg", "A4_Landscape_blank.svg"]:
        path = os.path.join(template_dir, candidate)
        if os.path.exists(path):
            template_file = path
            break
if template_file:
    page.Template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    page.Template.Template = template_file
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created page: {name} ({format})")
    finally:
        backend.disconnect()


@techdraw_group.command("view")
@click.option("--page", "-p", required=True, help="Page name.")
@click.option("--source", "-s", required=True,
              help="Semicolon-separated object names.")
@click.option("--direction", "-d", default="0,0,1",
              help="View direction vector as x,y,z.")
@click.option("--scale", default=1.0, type=float, help="View scale.")
@click.option("--name", "-n", help="View name.")
@_handle_error
def techdraw_view(page: str, source: str, direction: str,
                  scale: float, name: str | None) -> None:
    """Add a view to a TechDraw page."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        dx, dy, dz = [float(x) for x in direction.split(",")]
        source_names = [s.strip() for s in source.split(";") if s.strip()]
        source_list = ", ".join(f'doc.getObject("{s}")' for s in source_names)
        view_name = name or "View"

        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
page_obj = doc.getObject("{page}")
if page_obj is None:
    raise ValueError(f"Page '{page}' not found")
source_objects = [{source_list}]
source_objects = [obj for obj in source_objects if obj is not None]
if not source_objects:
    raise ValueError("No valid source objects found")
view = doc.addObject("TechDraw::DrawViewPart", "{view_name}")
view.Source = source_objects
view.Direction = FreeCAD.Vector({dx}, {dy}, {dz})
view.Scale = {scale}
page_obj.addView(view)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added view '{view_name}' to page '{page}'")
    finally:
        backend.disconnect()


@techdraw_group.command("dimension")
@click.option("--view", "-v", required=True, help="View name.")
@click.option("--type", "dim_type", default="distance",
              type=click.Choice(["distance", "radius", "diameter", "angle"]),
              help="Dimension type.")
@click.option("--elements", "-e",
              help="Semicolon-separated edge indices.")
@click.option("--text-position", "-tp",
              help="Text position as x,y.")
@click.option("--name", "-n", help="Dimension name.")
@_handle_error
def techdraw_dimension(view: str, dim_type: str, elements: str | None,
                       text_position: str | None, name: str | None) -> None:
    """Add a dimension to a TechDraw view."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        dim_name = name or f"Dimension_{dim_type.capitalize()}"
        elem_list = []
        if elements:
            elem_list = [int(x.strip()) for x in elements.split(";") if x.strip()]

        tp_line = ""
        if text_position:
            tx, ty = [float(x) for x in text_position.split(",")]
            tp_line = f"dim.FormatSpec = FreeCAD.Vector({tx}, {ty}, 0)"

        elem_str = ", ".join(str(e) for e in elem_list) if elem_list else ""

        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
view_obj = doc.getObject("{view}")
if view_obj is None:
    raise ValueError(f"View '{view}' not found")
# Get edges from the view
edges = view_obj.getVisibleEdges()
if not edges:
    raise ValueError("No visible edges in view")
# Select edges for dimensioning
selected_edges = []
{elem_str and f"elem_indices = [{elem_str}]" or ""}
{elem_str and "for idx in elem_indices:" or ""}
{elem_str and "    if 0 <= idx < len(edges):" or ""}
{elem_str and "        selected_edges.append(edges[idx])" or ""}
{elem_str and "    else:" or ""}
{elem_str and "        raise ValueError(f'Edge index {{idx}} out of range (0-{{len(edges)-1}})')" or ""}
{elem_str or "selected_edges = edges[:2] if len(edges) >= 2 else edges"}
# Create dimension based on type
dim_type = "{dim_type}"
if dim_type == "distance":
    dim = doc.addObject("TechDraw::DrawViewDimension", "{dim_name}")
    dim.MeasureType = "True"
    if len(selected_edges) >= 2:
        dim.Arbitrary = [selected_edges[0], selected_edges[1]]
    else:
        dim.Arbitrary = selected_edges
elif dim_type == "radius":
    dim = doc.addObject("TechDraw::DrawViewDimension", "{dim_name}")
    dim.MeasureType = "True"
    dim.FormatSpec = "R"
    dim.Arbitrary = selected_edges[:1] if selected_edges else []
elif dim_type == "diameter":
    dim = doc.addObject("TechDraw::DrawViewDimension", "{dim_name}")
    dim.MeasureType = "True"
    dim.FormatSpec = "%%c"
    dim.Arbitrary = selected_edges[:1] if selected_edges else []
elif dim_type == "angle":
    dim = doc.addObject("TechDraw::DrawViewDimension", "{dim_name}")
    dim.MeasureType = "True"
    if len(selected_edges) >= 2:
        dim.Arbitrary = [selected_edges[0], selected_edges[1]]
    else:
        dim.Arbitrary = selected_edges
{tp_line}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added {dim_type} dimension to view '{view}'")
    finally:
        backend.disconnect()


@techdraw_group.command("annotation")
@click.option("--page", "-p", required=True, help="Page name.")
@click.option("--text", "-t", required=True, help="Annotation text.")
@click.option("--position", "-pos", default="0,0",
              help="Position as x,y.")
@click.option("--name", "-n", help="Annotation name.")
@_handle_error
def techdraw_annotation(page: str, text: str, position: str,
                        name: str | None) -> None:
    """Add annotation text to a TechDraw page."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py = [float(x) for x in position.split(",")]
        anno_name = name or "Annotation"

        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
page_obj = doc.getObject("{page}")
if page_obj is None:
    raise ValueError(f"Page '{page}' not found")
anno = doc.addObject("TechDraw::DrawViewAnnotation", "{anno_name}")
anno.Text = "{text}"
anno.Position = FreeCAD.Vector({px}, {py}, 0)
page_obj.addView(anno)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added annotation to page '{page}'")
    finally:
        backend.disconnect()


@techdraw_group.command("symbol")
@click.option("--page", "-p", required=True, help="Page name.")
@click.option("--symbol", "-s", required=True,
              help="Symbol SVG file path.")
@click.option("--position", "-pos", default="0,0",
              help="Position as x,y.")
@click.option("--name", "-n", help="Symbol name.")
@_handle_error
def techdraw_symbol(page: str, symbol: str, position: str,
                    name: str | None) -> None:
    """Add a symbol to a TechDraw page."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py = [float(x) for x in position.split(",")]
        sym_name = name or "Symbol"
        symbol_path = os.path.abspath(symbol)

        code = f"""\
import FreeCAD
import TechDraw
import os
doc = FreeCAD.ActiveDocument
page_obj = doc.getObject("{page}")
if page_obj is None:
    raise ValueError(f"Page '{page}' not found")
symbol_path = r"{symbol_path}"
if not os.path.exists(symbol_path):
    raise ValueError(f"Symbol file not found: {symbol_path}")
sym = doc.addObject("TechDraw::DrawViewSymbol", "{sym_name}")
sym.Symbol = symbol_path
sym.Position = FreeCAD.Vector({px}, {py}, 0)
page_obj.addView(sym)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added symbol to page '{page}'")
    finally:
        backend.disconnect()


@techdraw_group.command("export")
@click.argument("page_name")
@click.option("--output", "-o", required=True,
              type=click.Path(), help="Output file path.")
@click.option("--format", "fmt",
              type=click.Choice(["svg", "pdf"]),
              help="Export format (auto-detected from extension).")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def techdraw_export(page_name: str, output: str, fmt: str | None,
                    overwrite: bool) -> None:
    """Export a TechDraw page to SVG or PDF."""
    from fc_cli.main import _output
    output_path = os.path.abspath(output)
    if os.path.exists(output_path) and not overwrite:
        _output.error(f"File exists: {output_path}", code="FILE_EXISTS",
                      suggestion="Use --overwrite to replace")
        return

    # Auto-detect format from extension
    if fmt is None:
        ext = os.path.splitext(output_path)[1].lower().lstrip(".")
        if ext in ("svg", "pdf"):
            fmt = ext
        else:
            _output.error(f"Cannot detect format from extension '.{ext}'",
                          code="INVALID_FORMAT",
                          suggestion="Use --format svg or --format pdf")
            return

    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
page = doc.getObject("{page_name}")
if page is None:
    raise ValueError(f"Page '{page_name}' not found")
output_path = r"{output_path}"
export_format = "{fmt}"
if export_format == "svg":
    page.exportSvg(output_path)
elif export_format == "pdf":
    page.exportPdf(output_path)
else:
    raise ValueError(f"Unsupported format: {{export_format}}")
"""
        r = backend.execute_code(code)
        if r.status == "ok":
            _output.output(r.to_dict(), f"Exported {fmt.upper()}: {output_path}")
        else:
            _output.error(f"{fmt.upper()} export failed", code="EXPORT_FAILED",
                          message=r.message)
    finally:
        backend.disconnect()


@techdraw_group.command("list")
@_handle_error
def techdraw_list() -> None:
    """List all TechDraw pages."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = """\
import FreeCAD
doc = FreeCAD.ActiveDocument
pages = [obj for obj in doc.Objects if obj.TypeId == "TechDraw::DrawPage"]
_fc_result = {
    "status": "ok",
    "data": {
        "pages": [{"name": p.Name, "label": p.Label, "view_count": p.Views.Count if hasattr(p, "Views") else len(p.Views)} for p in pages],
        "count": len(pages),
    },
    "message": ""
}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"{r.data.get('data', {}).get('count', 0)} page(s):")
    finally:
        backend.disconnect()


@techdraw_group.command("get")
@click.argument("name")
@_handle_error
def techdraw_get(name: str) -> None:
    """Get details of a TechDraw page."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
page = doc.getObject("{name}")
if page is None:
    raise ValueError(f"Page '{name}' not found")
views = []
for v in page.Views:
    views.append({{"name": v.Name, "label": v.Label, "type": v.TypeId}})
template_info = None
if hasattr(page, "Template") and page.Template:
    tmpl = page.Template
    template_info = {{"name": tmpl.Name}}
    if hasattr(tmpl, "Template"):
        template_info["file"] = tmpl.Template
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": page.Name,
        "label": page.Label,
        "view_count": len(page.Views),
        "views": views,
        "template": template_info,
    }},
    "message": ""
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"Page '{name}':")
    finally:
        backend.disconnect()


@techdraw_group.command("section")
@click.option("--page", "-p", required=True, help="Page name.")
@click.option("--source", "-s", required=True, help="View name to create section from.")
@click.option("--direction", "-d", default="horizontal",
              type=click.Choice(["horizontal", "vertical", "custom"]),
              help="Section direction.")
@click.option("--position", default="0,0,0", help="Cut position as x,y,z.")
@click.option("--name", "-n", help="Section view name.")
@_handle_error
def techdraw_section(page: str, source: str, direction: str,
                     position: str, name: str | None) -> None:
    """Create a section view in a TechDraw page."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py, pz = [float(x) for x in position.split(",")]
        view_name = name or f"Section_{source}"
        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
page_obj = doc.getObject("{page}")
if page_obj is None:
    raise ValueError(f"Page '{page}' not found")
view = doc.getObject("{source}")
if view is None:
    raise ValueError(f"View '{source}' not found")
section = doc.addObject("TechDraw::DrawViewSection", "{view_name}")
section.Source = [view]
section.Direction = FreeCAD.Vector({px}, {py}, {pz})
page_obj.addView(section)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created section view: {view_name}")
    finally:
        backend.disconnect()


@techdraw_group.command("detail")
@click.option("--page", "-p", required=True, help="Page name.")
@click.option("--source", "-s", required=True, help="Source view name.")
@click.option("--center", required=True, help="Detail center as x,y,z.")
@click.option("--radius", default=20.0, type=float, help="Detail radius.")
@click.option("--scale", default=2.0, type=float, help="Detail scale.")
@click.option("--name", "-n", help="Detail view name.")
@_handle_error
def techdraw_detail(page: str, source: str, center: str,
                    radius: float, scale: float, name: str | None) -> None:
    """Create a detail (enlarged) view in a TechDraw page."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy, cz = [float(x) for x in center.split(",")]
        view_name = name or f"Detail_{source}"
        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
page_obj = doc.getObject("{page}")
if page_obj is None:
    raise ValueError(f"Page '{page}' not found")
view = doc.getObject("{source}")
if view is None:
    raise ValueError(f"View '{source}' not found")
detail = doc.addObject("TechDraw::DrawViewDetail", "{view_name}")
detail.Source = [view]
detail.Center = FreeCAD.Vector({cx}, {cy}, {cz})
detail.Radius = {radius}
detail.Scale = {scale}
page_obj.addView(detail)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created detail view: {view_name}")
    finally:
        backend.disconnect()


@techdraw_group.command("centerline")
@click.option("--view", "-v", required=True, help="View name.")
@click.option("--elements", "-e", required=True, help="Edge indices (comma-sep).")
@click.option("--name", "-n", help="Centerline name.")
@_handle_error
def techdraw_centerline(view: str, elements: str, name: str | None) -> None:
    """Add centerlines to a TechDraw view."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cl_name = name or f"Centerline_{view}"
        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
view_obj = doc.getObject("{view}")
if view_obj is None:
    raise ValueError(f"View '{view}' not found")
cl = doc.addObject("TechDraw::DrawViewWeld", "{cl_name}")
cl.View = view_obj
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added centerline to view '{view}'")
    finally:
        backend.disconnect()


@techdraw_group.command("hatch")
@click.option("--view", "-v", required=True, help="View name.")
@click.option("--pattern", default="ANSI31", help="Hatch pattern name.")
@click.option("--scale", default=1.0, type=float, help="Hatch scale.")
@click.option("--color", default="0,0,0", help="Hatch color as r,g,b.")
@_handle_error
def techdraw_hatch(view: str, pattern: str, scale: float, color: str) -> None:
    """Add hatch pattern to a TechDraw view."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r_val, g_val, b_val = [float(x) for x in color.split(",")]
        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
view_obj = doc.getObject("{view}")
if view_obj is None:
    raise ValueError(f"View '{view}' not found")
hatch = doc.addObject("TechDraw::DrawHatch", "Hatch_{view}")
hatch.Source = view_obj
hatch.HatchPattern = "{pattern}"
hatch.HatchScale = {scale}
hatch.Color = FreeCAD.Color({r_val}, {g_val}, {b_val})
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added hatch to view '{view}'")
    finally:
        backend.disconnect()


@techdraw_group.command("table")
@click.option("--page", "-p", required=True, help="Page name.")
@click.option("--position", "-pos", default="10,10", help="Table position as x,y.")
@click.option("--name", "-n", default="PartsList", help="Table name.")
@_handle_error
def techdraw_table(page: str, position: str, name: str) -> None:
    """Create a parts list / BOM table in a TechDraw page."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py = [float(x) for x in position.split(",")]
        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
page_obj = doc.getObject("{page}")
if page_obj is None:
    raise ValueError(f"Page '{page}' not found")
table = doc.addObject("TechDraw::DrawViewSpreadsheet", "{name}")
page_obj.addView(table)
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{name}", "parts_count": len(doc.Objects)}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created BOM table: {name}")
    finally:
        backend.disconnect()


@techdraw_group.command("delete-view")
@click.argument("name")
@_handle_error
def techdraw_delete_view(name: str) -> None:
    """Delete a view from a TechDraw page."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import TechDraw
doc = FreeCAD.ActiveDocument
view = doc.getObject("{name}")
if view is None:
    raise ValueError(f"View '{name}' not found")
if hasattr(view, "InList") and view.InList:
    for page in view.InList:
        if hasattr(page, "removeView"):
            page.removeView(view)
doc.removeObject("{name}")
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Deleted view: {name}")
    finally:
        backend.disconnect()
