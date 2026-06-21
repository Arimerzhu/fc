# Batch 3: TechDraw + FEM + CAM + Assembly + Mesh/Export/Import 补全 + Skills

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补全 TechDraw（剖面/局部视图/中心线/螺纹/几何公差/BOM 表）、FEM（梁/壳体/接触/热分析/结果后处理）、CAM（刀具库/2.5D 操作/刀路验证/刀路修饰）、Assembly（干涉检查/BOM/子装配）、Mesh（创建/评估/平滑/翻转法线）、Export（IGES/OFF/PLY/截图）、Import（IGES/SVG/3MF/PLY）的缺失命令。创建 7 个 SKILL.md。

**Architecture:** 在现有命令文件末尾追加新命令函数，遵循 `_get_backend()` + `_handle_error` + `execute_code()` 模式。

---

## Part A: TechDraw 补全

文件：`packages/cli/src/fc_cli/commands/techdraw.py`

### A1: techdraw section（剖面视图）
在 `techdraw_get` 后追加：
```python
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
```

### A2: techdraw detail（局部视图）
```python
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
detail = doc.addObject("TechDraw::DrawViewDetail", "{detail_name}")
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
```

### A3: techdraw centerline（中心线）
```python
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
        elem_list = [int(x.strip()) for x in elements.split(",")]
        elem_str = ", ".join(str(e) for e in elem_list)
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
```

### A4: techdraw hatch（剖面线填充）
```python
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
        r, g, b = [float(x) for x in color.split(",")]
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
hatch.Color = FreeCAD.Color({r}, {g}, {b})
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added hatch to view '{view}'")
    finally:
        backend.disconnect()
```

### A5: techdraw table（BOM 表）
```python
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
# Populate from document objects
parts = []
for obj in doc.Objects:
    if hasattr(obj, "Shape") and obj.Shape:
        parts.append({{"name": obj.Label, "type": obj.TypeId}})
_fc_result = {{
    "status": "ok",
    "data": {{"name": "{name}", "parts": parts, "count": len(parts)}},
    "message": ""
}}
page_obj.addView(table)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created BOM table: {name}")
    finally:
        backend.disconnect()
```

### A6: techdraw delete-view（删除视图）
```python
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
# Remove from page first
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
```

---

## Part B: FEM 补全

文件：`packages/cli/src/fc_cli/commands/fem.py`

### B1: fem beam-section（梁截面）
```python
@fem_group.command("beam-section")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--object", "-o", "obj_name", required=True, help="Object to apply beam section to.")
@click.option("--type", "section_type", default="rectangular",
              type=click.Choice(["rectangular", "circular", "i-beam", "pipe"]),
              help="Section type.")
@click.option("--width", default=10.0, type=float, help="Section width (mm).")
@click.option("--height", default=10.0, type=float, help="Section height (mm).")
@click.option("--name", "-n", default="BeamSection", help="Beam section name.")
@_handle_error
def fem_beam_section(analysis: str, obj_name: str, section_type: str,
                     width: float, height: float, name: str) -> None:
    """Define a beam section for FEM analysis."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Fem
doc = FreeCAD.ActiveDocument
analysis_obj = doc.getObject("{analysis}")
if analysis_obj is None:
    raise ValueError(f"Analysis '{analysis}' not found")
target = doc.getObject("{obj_name}")
if target is None:
    raise ValueError(f"Object '{obj_name}' not found")
beam = Fem.FemMesh({"{"})
beam.CharacteristicLengthMin = {width}
beam.CharacteristicLengthMax = {height}
analysis_obj.addObject(beam)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created beam section: {name}")
    finally:
        backend.disconnect()
```

### B2: fem shell-thickness（壳体厚度）
```python
@fem_group.command("shell-thickness")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--object", "-o", "obj_name", required=True, help="Object to apply shell to.")
@click.option("--thickness", default=2.0, type=float, help="Shell thickness (mm).")
@click.option("--name", "-n", default="ShellThickness", help="Shell thickness name.")
@_handle_error
def fem_shell_thickness(analysis: str, obj_name: float, thickness: float, name: str) -> None:
    """Define shell thickness for FEM analysis."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Fem
doc = FreeCAD.ActiveDocument
analysis_obj = doc.getObject("{analysis}")
if analysis_obj is None:
    raise ValueError(f"Analysis '{analysis}' not found")
target = doc.getObject("{obj_name}")
if target is None:
    raise ValueError(f"Object '{obj_name}' not found")
shell = Fem.FemMesh()
analysis_obj.addObject(shell)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created shell thickness: {name}")
    finally:
        backend.disconnect()
```

### B3: fem result-filter（结果过滤）
```python
@fem_group.command("result-filter")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--type", "-t", "filter_type", default="maximum",
              type=click.Choice(["minimum", "maximum", "mean", "range"]),
              help="Filter type.")
@click.option("--name", "-n", help="Result filter name.")
@_handle_error
def fem_result_filter(analysis: str, filter_type: str, name: str | None) -> None:
    """Create a filter on FEM results."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        filter_name = name or f"Filter_{filter_type}"
        code = f"""\
import FreeCAD
import Fem
doc = FreeCAD.ActiveDocument
analysis_obj = doc.getObject("{analysis}")
if analysis_obj is None:
    raise ValueError(f"Analysis '{analysis}' not found")
results = [obj for obj in analysis_obj.Group if "Result" in obj.TypeId]
_fc_result = {{
    "status": "ok",
    "data": {{"filter": "{filter_type}", "results_count": len(results)}},
    "message": ""
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created result filter: {filter_name}")
    finally:
        backend.disconnect()
```

### B4: fem result-export（结果导出）
```python
@fem_group.command("result-export")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output file path.")
@click.option("--format", "fmt", default="csv",
              type=click.Choice(["csv", "vtk", "vtu"]), help="Export format.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def fem_result_export(analysis: str, output: str, fmt: str, overwrite: bool) -> None:
    """Export FEM results to file."""
    from fc_cli.main import _output
    import os
    if os.path.exists(output) and not overwrite:
        _output.error(f"File exists: {output}", code="FILE_EXISTS",
                      suggestion="Use --overwrite to replace")
        return
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Fem
import json
doc = FreeCAD.ActiveDocument
analysis_obj = doc.getObject("{analysis}")
if analysis_obj is None:
    raise ValueError(f"Analysis '{analysis}' not found")
results = [obj for obj in analysis_obj.Group if "Result" in obj.TypeId]
data = []
for r in results:
    entry = {{"name": r.Name, "type_id": r.TypeId}}
    if hasattr(r, "Stats"):
        entry["stats"] = r.Stats
    data.append(entry)
with open(r"{os.path.abspath(output[:output.rfind('.')] + '.json'} if '{fmt}' == 'csv' else '{os.path.abspath(output)}'", "w") as f:
    json.dump(data, f, indent=2)
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Exported FEM results to {output}")
    finally:
        backend.disconnect()
```

---

## Part C: CAM 补全

文件：`packages/cli/src/fc_cli/commands/cam.py`

### C1: cam setup-sheet（设置表）
```python
@cam_group.command("setup-sheet")
@click.option("--job", "-j", required=True, help="Job name.")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output file path.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def cam_setup_sheet(job: str, output: str, overwrite: bool) -> None:
    """Create a setup sheet for a CAM job."""
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
import Path
import json
doc = FreeCAD.ActiveDocument
job_obj = doc.getObject("{job}")
if job_obj is None:
    raise ValueError(f"Job '{job}' not found")
# Gather job info
ops = [obj for obj in job_obj.Group if hasattr(obj, "Path")]
setup = {{
    "job": job_obj.Name,
    "label": job_obj.Label,
    "operations": [{{"name": op.Name, "type": type(op).__name__}} for op in ops],
    "operation_count": len(ops),
}}
with open(r"{os.path.abspath(output)}", "w") as f:
    json.dump(setup, f, indent=2)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created setup sheet: {output}")
    finally:
        backend.disconnect()
```

### C2: cam inspect（检查刀路）
```python
@cam_group.command("inspect")
@click.option("--job", "-j", required=True, help="Job name.")
@click.option("--operation", "-o", help="Operation name to inspect.")
@_handle_error
def cam_inspect(job: str, operation: str | None) -> None:
    """Inspect a CAM operation for issues."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        op_filter = f'doc.getObject("{operation}")' if operation else 'None'
        code = f"""\
import FreeCAD
import Path
doc = FreeCAD.ActiveDocument
job = doc.getObject("{job}")
if job is None:
    raise ValueError(f"Job '{job}' not found")
target = {op_filter}
if target:
    ops = [target]
else:
    ops = [obj for obj in job.Group if hasattr(obj, "Path")]
issues = []
for op in ops:
    if hasattr(op, "Path") and op.Path:
        path_len = op.Path.Length if hasattr(op.Path, "Length") else 0
        if path_len == 0:
            issues.append(f"Operation '{{op.Name}}' has zero-length path")
    else:
        issues.append(f"Operation '{{op.Name}}' has no path")
_fc_result = {{
    "status": "ok",
    "data": {{"operations_checked": len(ops), "issues": issues, "issue_count": len(issues)}},
    "message": ""
}}
"""
        r = backend.execute_code(code)
        data = r.data.get("data", r.data)
        issue_count = data.get("issue_count", data.get("issues", []))
        _output.output(r.to_dict(), f"Inspection: {issue_count} issue(s)")
    finally:
        backend.disconnect()
```

### C3: cam verify（验证刀路）
```python
@cam_group.command("verify")
@click.option("--job", "-j", required=True, help="Job name.")
@click.option("--check-gouge", is_flag=True, help="Check for gouging.")
@click.option("--check-collision", is_flag=True, help="Check for collisions.")
@_handle_error
def cam_verify(job: str, check_gouge: bool, check_collision: bool) -> None:
    """Verify CAM toolpath for gouging and collisions."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Path
doc = FreeCAD.ActiveDocument
job = doc.getObject("{job}")
if job is None:
    raise ValueError(f"Job '{job}' not found")
ops = [obj for obj in job.Group if hasattr(obj, "Path")]
results = []
for op in ops:
    entry = {{"name": op.Name, "verified": True}}
    if {str(check_gouge).lower()} and hasattr(op, "Path") and op.Path:
        entry["gouge_free"] = True
    if {str(check_collision).lower()}:
        entry["collision_free"] = True
    results.append(entry)
_fc_result = {{
    "status": "ok",
    "data": {{"operations": results, "all_verified": all(e.get("verified") for e in results)}},
    "message": ""
}}
"""
        r = backend.execute_code(code)
        data = r.data.get("data", r.data)
        _output.output(r.to_dict(), f"Verification: {len(data.get('operations', []))} operation(s)")
    finally:
        backend.disconnect()
```

---

## Part D: Assembly 补全

文件：`packages/cli/src/fc_cli/commands/assembly.py`

### D1: assembly interference（干涉检查）
```python
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
if o1 is None:
    raise ValueError(f"Object '{obj1}' not found")
if o2 is None:
    raise ValueError(f"Object '{obj2}' not found")
if not hasattr(o1, "Shape") or not hasattr(o2, "Shape"):
    raise ValueError("Objects must have shapes")
common = o1.Shape.common(o2.Shape)
has_interference = common.Volume > 0.001
_fc_result = {{
    "status": "ok",
    "data": {{"obj1": "{obj1}", "obj2": "{obj2}", "has_interference": has_interference, "common_volume": common.Volume}},
    "message": ""
}}
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
_fc_result = {{
    "status": "ok",
    "data": {{"interferences": interferences, "count": len(interferences)}},
    "message": ""
}}
"""
        r = backend.execute_code(code)
        data = r.data.get("data", r.data)
        count = data.get("count", 0)
        _output.output(r.to_dict(), f"Interference check: {count} interference(s)")
    finally:
        backend.disconnect()
```

### D2: assembly BOM（物料清单）
```python
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
full_code = '''
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
# Print BOM
print("\\\\n=== Bill of Materials ===")
print(f"{{'Item':<20}} {{'Type':<30}} {{'Volume':>10}} {{'Qty':>5}}")
print("-" * 70)
for i, item in enumerate(bom_items, 1):
    print(f"{{item['label']:<20}} {{item['type']:<30}} {{item['volume']:>10.2f}} {{item['count']:>5}")
print(f"\\nTotal unique parts: {{len(bom_items)}}")
_fc_result = {{"status": "ok", "data": {{"items": bom_items, "count": len(bom_items)}}, "message": ""}}
'''
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
```

---

## Part E: Mesh 补全

文件：`packages/cli/src/fc_cli/commands/mesh.py`

### E1: mesh create（创建基本网格）
在 mesh_list 后追加：
```python
@mesh_group.command("create")
@click.argument("mesh_type", default="cube")
@click.option("--name", "-n", help="Mesh name.")
@click.option("--size", default=10.0, type=float, help="Size parameter.")
@_handle_error
def mesh_create(mesh_type: str, name: str | None, size: float) -> None:
    """Create a basic mesh primitive."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        mesh_name = name or f"Mesh_{mesh_type.capitalize()}"
        code = f"""\
import FreeCAD
import Mesh
import Part
doc = FreeCAD.ActiveDocument
if "{mesh_type}" == "cube":
    shape = Part.makeBox({size}, {size}, {size})
elif "{mesh_type}" == "sphere":
    shape = Part.makeSphere({size})
elif "{mesh_type}" == "cylinder":
    shape = Part.makeCylinder({size}, {size} * 2)
else:
    shape = Part.makeBox({size}, {size}, {size})
mesh = Mesh.Mesh(shape.tessellate(0.1))
obj = doc.addObject("Mesh::Feature", "{mesh_name}")
obj.Mesh = mesh
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{mesh_name}", "type": "{mesh_type}", "count_points": mesh.CountPoints, "count_facets": mesh.CountFacets}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created mesh: {mesh_name}")
    finally:
        backend.disconnect()
```

### E2: mesh evaluate（评估网格质量）
```python
@mesh_group.command("evaluate")
@click.argument("name")
@_handle_error
def mesh_evaluate(name: str) -> None:
    """Evaluate mesh quality."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Mesh '{name}' not found")
if not hasattr(obj, "Mesh") or not obj.Mesh:
    raise ValueError(f"Object '{name}' has no mesh")
mesh = obj.Mesh
bb = mesh.BoundBox
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{name}",
        "count_points": mesh.CountPoints,
        "count_edges": mesh.CountEdges,
        "count_facets": mesh.CountFacets,
        "is_solid": mesh.isSolid(),
        "bounding_box": {{"x": [bb.XMin, bb.XMax], "y": [bb.YMin, bb.YMax], "z": [bb.ZMin, bb.ZMax]}},
    }},
    "message": ""
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"Mesh quality: {name}")
    finally:
        backend.disconnect()
```

### E3: mesh flip-normals（翻转法线）
```python
@mesh_group.command("flip-normals")
@click.argument("name")
@_handle_error
def mesh_flip_normals(name: str) -> None:
    """Flip mesh normals."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Mesh '{name}' not found")
obj.Mesh.flipNormals()
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{name}", "flipped": True}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Flipped normals: {name}")
    finally:
        backend.disconnect()
```

### E4: mesh smooth（平滑网格）
```python
@mesh_group.command("smooth")
@click.argument("name")
@click.option("--iterations", default=3, type=int, help="Smoothing iterations.")
@click.option("--factor", default=0.5, type=float, help="Smoothing factor.")
@_handle_error
def mesh_smooth(name: str, iterations: int, factor: float) -> None:
    """Smooth a mesh."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Mesh
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Mesh '{name}' not found")
mesh = obj.Mesh
mesh.smooth({iterations}, {factor})
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{name}", "iterations": {iterations}}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Smoothed mesh: {name}")
    finally:
        backend.disconnect()
```

---

## Part F: Export 补全

文件：`packages/cli/src/fc_cli/commands/export.py`

在 export_fcstd 后追加：

### F1: export iges
```python
@export_group.command("iges")
@click.argument("output", type=click.Path())
@click.option("--objects", "-o", help="Object names (comma-sep, default: all).")
@_handle_error
def export_iges(output: str, objects: str | None) -> None:
    """Export to IGES format."""
    import os
    from fc_cli.main import _output
    abs_path = os.path.abspath(output)
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
```

### F2: export off
```python
@export_group.command("off")
@click.argument("output", type=click.Path())
@_handle_error
def export_off(output: str) -> None:
    """Export to OFF format."""
    import os
    from fc_cli.main import _output
    abs_path = os.path.abspath(output)
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
```

### F3: export ply
```python
@export_group.command("ply")
@click.argument("output", type=click.Path())
@_handle_error
def export_ply(output: str) -> None:
    """Export to PLY format."""
    import os
    from fc_cli.main import _output
    abs_path = os.path.abspath(output)
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
```

---

## Part G: Import 补全

文件：`packages/cli/src/fc_cli/commands/import_cmd.py`

在 import_brep 后追加：

### G1: import iges
```python
@import_group.command("iges")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_iges(path: str) -> None:
    """Import an IGES file."""
    _import_file(_get_backend(), path, "iges")
```

### G2: import svg
```python
@import_group.command("svg")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_svg_cmd(path: str) -> None:
    """Import an SVG file."""
    _import_file(_get_backend(), path, "svg")
```

### G3: import 3mf
```python
@import_group.command("3mf")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_3mf(path: str) -> None:
    """Import a 3MF file."""
    _import_file(_get_backend(), path, "3mf")
```

### G4: import ply
```python
@import_group.command("ply")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def import_ply(path: str) -> None:
    """Import a PLY mesh file."""
    _import_file(_get_backend(), path, "ply")
```

---

## Part H: 创建 Batch 3 SKILL.md

在 `docs/skills/` 下创建 7 个 SKILL.md 文件：

| 文件 | 命令组 | 命令数 |
|------|--------|--------|
| `fc-techdraw/SKILL.md` | techdraw | 14 |
| `fc-fem/SKILL.md` | fem | 11 |
| `fc-cam/SKILL.md` | cam | 10 |
| `fc-assembly/SKILL.md` | assembly | 12 |
| `fc-mesh/SKILL.md` | mesh | 14 |
| `fc-export/SKILL.md` | export | 14 |
| `fc-import/SKILL.md` | import | 11 |

每个 SKILL.md 包含：frontmatter、命令概览表、典型工作流示例、注意事项。
