"""Spreadsheet commands.

Commands for Spreadsheet workbench operations:
  spreadsheet create   — Create a new spreadsheet
  spreadsheet set      — Set a cell value
  spreadsheet get      — Get a cell value
  spreadsheet formula  — Set a cell formula
  spreadsheet alias    — Set a cell alias
  spreadsheet link     — Link a cell to a parameter
  spreadsheet show     — Display the spreadsheet
  spreadsheet list     — List all spreadsheets
  spreadsheet clear    — Clear a cell or range
  spreadsheet export   — Export to CSV
  spreadsheet import   — Import from CSV
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


@click.group("spreadsheet")
def spreadsheet_group():
    """Spreadsheet workbench commands."""
    pass


@spreadsheet_group.command("create")
@click.option("--name", "-n", default="Spreadsheet", help="Spreadsheet name.")
@_handle_error
def spreadsheet_create(name: str) -> None:
    """Create a new spreadsheet."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Spreadsheet
doc = FreeCAD.ActiveDocument
sheet = doc.getObject("{name}")
if sheet is not None:
    raise ValueError(f"Spreadsheet '{name}' already exists")
sheet = doc.addObject("App::FeaturePython", "{name}")
Spreadsheet.Sheet(sheet)
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{name}"}}, "message": "Created spreadsheet: {name}"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created spreadsheet: {name}")
    finally:
        backend.disconnect()


@spreadsheet_group.command("set")
@click.option("--sheet", "-s", required=True, help="Spreadsheet name.")
@click.option("--cell", "-c", required=True, help="Cell reference (e.g. A1).")
@click.option("--value", "-v", required=True, help="Value to set.")
@_handle_error
def spreadsheet_set(sheet: str, cell: str, value: str) -> None:
    """Set a cell value."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Spreadsheet
doc = FreeCAD.ActiveDocument
s = doc.getObject("{sheet}")
if s is None:
    raise ValueError(f"Spreadsheet '{sheet}' not found")
s.set("{cell}", "{value}")
doc.recompute()
val = s.get("{cell}")
_fc_result = {{"status": "ok", "data": {{"cell": "{cell}", "value": str(val)}}}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Set {sheet}.{cell} = {value}")
    finally:
        backend.disconnect()


@spreadsheet_group.command("get")
@click.option("--sheet", "-s", required=True, help="Spreadsheet name.")
@click.option("--cell", "-c", required=True, help="Cell reference (e.g. A1).")
@_handle_error
def spreadsheet_get(sheet: str, cell: str) -> None:
    """Get a cell value."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Spreadsheet
doc = FreeCAD.ActiveDocument
s = doc.getObject("{sheet}")
if s is None:
    raise ValueError(f"Spreadsheet '{sheet}' not found")
val = s.get("{cell}")
alias = s.getAlias("{cell}")
_fc_result = {{"status": "ok", "data": {{"cell": "{cell}", "value": str(val) if val is not None else None, "alias": str(alias) if alias else None}}}}
"""
        r = backend.execute_code(code)
        data = r.data.get("data", r.data)
        val = data.get("value")
        alias = data.get("alias")
        msg = f"{sheet}.{cell} = {val}"
        if alias:
            msg += f" (alias: {alias})"
        _output.output(r.to_dict(), msg)
    finally:
        backend.disconnect()


@spreadsheet_group.command("formula")
@click.option("--sheet", "-s", required=True, help="Spreadsheet name.")
@click.option("--cell", "-c", required=True, help="Cell reference (e.g. A1).")
@click.option("--formula", "-f", required=True, help="Formula string (e.g. =A1+B1).")
@_handle_error
def spreadsheet_formula(sheet: str, cell: str, formula: str) -> None:
    """Set a cell formula."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Spreadsheet
doc = FreeCAD.ActiveDocument
s = doc.getObject("{sheet}")
if s is None:
    raise ValueError(f"Spreadsheet '{sheet}' not found")
s.set("{cell}", "{formula}", "formula")
doc.recompute()
val = s.get("{cell}")
_fc_result = {{"status": "ok", "data": {{"cell": "{cell}", "formula": "{formula}", "value": str(val)}}}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Set formula {sheet}.{cell} = {formula}")
    finally:
        backend.disconnect()


@spreadsheet_group.command("alias")
@click.option("--sheet", "-s", required=True, help="Spreadsheet name.")
@click.option("--cell", "-c", required=True, help="Cell reference (e.g. A1).")
@click.option("--alias", "-a", required=True, help="Alias name for the cell.")
@_handle_error
def spreadsheet_alias(sheet: str, cell: str, alias: str) -> None:
    """Set a cell alias."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Spreadsheet
doc = FreeCAD.ActiveDocument
s = doc.getObject("{sheet}")
if s is None:
    raise ValueError(f"Spreadsheet '{sheet}' not found")
s.setAlias("{cell}", "{alias}")
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"cell": "{cell}", "alias": "{alias}"}}}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Set alias {sheet}.{cell} = {alias}")
    finally:
        backend.disconnect()


@spreadsheet_group.command("link")
@click.option("--sheet", "-s", required=True, help="Spreadsheet name.")
@click.option("--cell", "-c", required=True, help="Cell reference (e.g. A1).")
@click.option("--object", "-o", "obj_name", required=True, help="Object name in the document.")
@click.option("--property", "-p", "prop_name", required=True, help="Property name on the object.")
@_handle_error
def spreadsheet_link(sheet: str, cell: str, obj_name: str, prop_name: str) -> None:
    """Link a cell to a document property."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Spreadsheet
doc = FreeCAD.ActiveDocument
s = doc.getObject("{sheet}")
if s is None:
    raise ValueError(f"Spreadsheet '{sheet}' not found")
target = doc.getObject("{obj_name}")
if target is None:
    raise ValueError(f"Object '{obj_name}' not found")
if not hasattr(target, "{prop_name}"):
    raise ValueError(f"Object '{obj_name}' has no property '{prop_name}'")
val = s.get("{cell}")
_fc_result = {{"status": "ok", "data": {{"cell": "{cell}", "value": str(val), "linked_to": "{obj_name}.{prop_name}"}}}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Linked {sheet}.{cell} to {obj_name}.{prop_name}")
    finally:
        backend.disconnect()


@spreadsheet_group.command("show")
@click.option("--sheet", "-s", required=True, help="Spreadsheet name.")
@click.option("--range", "-r", default="A1:Z20", help="Range to display (e.g. A1:Z20).")
@_handle_error
def spreadsheet_show(sheet: str, range: str) -> None:
    """Display spreadsheet contents."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Spreadsheet
doc = FreeCAD.ActiveDocument
s = doc.getObject("{sheet}")
if s is None:
    raise ValueError(f"Spreadsheet '{sheet}' not found")
# Parse range
import re
m = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", "{range}")
if not m:
    raise ValueError("Invalid range format. Use A1:Z20 style.")
col_start = m.group(1)
row_start = int(m.group(2))
col_end = m.group(3)
row_end = int(m.group(4))
def col_to_num(c):
    n = 0
    for ch in c:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n
def num_to_col(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s
cs = col_to_num(col_start)
ce = col_to_num(col_end)
cells = []
for row in range(row_start, row_end + 1):
    for col in range(cs, ce + 1):
        addr = f"{{num_to_col(col)}}{{row}}"
        val = s.get(addr)
        alias = s.getAlias(addr)
        if val is not None or alias:
            cells.append({{"cell": addr, "value": str(val) if val is not None else None, "alias": alias}})
_fc_result = {{"status": "ok", "data": {{"range": "{range}", "cells": cells}}}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"{sheet} [{range}]:")
    finally:
        backend.disconnect()


@spreadsheet_group.command("list")
@_handle_error
def spreadsheet_list() -> None:
    """List all spreadsheets in the current document."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = """\
import FreeCAD
doc = FreeCAD.ActiveDocument
sheets = [obj for obj in doc.Objects if obj.TypeId == "App::FeaturePython" if "Spreadsheet" in obj.Module if hasattr(obj, "Proxy") and obj.Proxy is not None]
# Also check for Spreadsheet::Sheet type
sheets2 = [obj for obj in doc.Objects if "Spreadsheet" in obj.TypeId if "Spreadsheet" in obj.TypeId]
all_sheets = {s.Name: s for s in sheets + sheets2}
_fc_result = {
    "status": "ok",
    "data": {"spreadsheets": [{"name": s.Name, "label": s.Label, "TypeId": s.TypeId} for s in all_sheets.values()], "count": len(all_sheets)},
    "message": ""
}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"{r.data.get('data', {}).get('count', 0)} spreadsheet(s):")
    finally:
        backend.disconnect()


@spreadsheet_group.command("clear")
@click.option("--sheet", "-s", required=True, help="Spreadsheet name.")
@click.option("--cell", "-c", help="Single cell to clear (e.g. A1).")
@click.option("--range", "-r", help="Range to clear (e.g. A1:C10).")
@_handle_error
def spreadsheet_clear(sheet: str, cell: str | None, range: str | None) -> None:
    """Clear a cell or range of cells."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        if cell:
            code = f"""\
import FreeCAD
import Spreadsheet
doc = FreeCAD.ActiveDocument
s = doc.getObject("{sheet}")
if s is None:
    raise ValueError(f"Spreadsheet '{sheet}' not found")
s.clear("{cell}")
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"cleared": "{cell}"}}}}
"""
        elif range:
            code = f"""\
import FreeCAD
import Spreadsheet
doc = FreeCAD.ActiveDocument
s = doc.getObject("{sheet}")
if s is None:
    raise ValueError(f"Spreadsheet '{sheet}' not found")
s.clear("{range}")
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"cleared": "{range}"}}}}
"""
        else:
            _output.error("Specify --cell or --range", code="MISSING_ARGUMENT",
                          suggestion="Use --cell A1 or --range A1:C10")
            return
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Cleared {sheet}")
    finally:
        backend.disconnect()


@spreadsheet_group.command("export")
@click.option("--sheet", "-s", required=True, help="Spreadsheet name.")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output CSV file path.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def spreadsheet_export(sheet: str, output: str, overwrite: bool) -> None:
    """Export spreadsheet to CSV."""
    import os
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
import Spreadsheet
import csv
doc = FreeCAD.ActiveDocument
s = doc.getObject("{sheet}")
if s is None:
    raise ValueError(f"Spreadsheet '{sheet}' not found")
import re
# Gather all used cells
cells = {{}}
max_row = 0
max_col = 0
for addr in s.PropertiesList:
    if hasattr(s, addr):
        continue
    m = re.match(r"([A-Z]+)(\d+)", addr)
    if m:
        col_str = m.group(1)
        row = int(m.group(2))
        col = 0
        for ch in col_str:
            col = col * 26 + (ord(ch) - ord("A") + 1)
        val = s.get(addr)
        if val is not None:
            cells[(row - 1, col - 1)] = str(val)
            max_row = max(max_row, row)
            max_col = max(max_col, col)
data = []
for r in range(max_row):
    row_data = []
    for c in range(max_col):
        row_data.append(cells.get((r, c), ""))
    data.append(row_data)
with open(r"{os.path.abspath(output)}", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(data)
_fc_result = {{"status": "ok", "data": {{"rows": len(data), "file": r"{os.path.abspath(output)}"}}}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Exported {sheet} to {output}")
    finally:
        backend.disconnect()


@spreadsheet_group.command("import")
@click.option("--sheet", "-s", required=True, help="Target spreadsheet name.")
@click.option("--input", "-i", required=True, type=click.Path(exists=True), help="Input CSV file path.")
@_handle_error
def spreadsheet_import(sheet: str, input: str) -> None:
    """Import spreadsheet from CSV."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Spreadsheet
import csv
doc = FreeCAD.ActiveDocument
s = doc.getObject("{sheet}")
if s is None:
    raise ValueError(f"Spreadsheet '{sheet}' not found")
def num_to_col(n):
    s = ""
    while n >= 0:
        s = chr(65 + n % 26) + s
        n = n // 26 - 1
    return s if s else "A"
count = 0
with open(r"{input}", "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row_idx, row in enumerate(reader):
        for col_idx, val in enumerate(row):
            if val.strip():
                addr = f"{{num_to_col(col_idx)}}{{row_idx + 1}}"
                s.set(addr, val.strip())
                count += 1
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"cells_imported": count}}}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Imported {count} cells into {sheet}")
    finally:
        backend.disconnect()
