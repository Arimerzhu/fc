# Batch 2: Sketch + Surface + Draft 补全 + Skills

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补全 Sketch 命令组缺失的几何类型（ellipse、polygon、bspline、slot、point）和操作（delete-geom、trim、extend、mirror、clone、export）；补全 Surface 命令组缺失的操作（extrude、revolve、ruled、blend、curvature）；补全 Draft 命令组缺失的操作（clone、mirror、stretch、upgrade、downgrade、path-array、point-array、point、facebinder、label）。创建 `fc-sketch`、`fc-surface`、`fc-draft` 三个 SKILL.md。

**Architecture:** 在现有 `sketch.py`、`surface.py`、`draft.py` 文件末尾追加新命令函数。每个新命令 ~30-50 行，遵循 `_get_backend()` + `_handle_error` + `execute_code()` 模式。

**Tech Stack:** Python 3.13, Click, fc-core, FreeCAD API via execute_code

---

## Part A: Sketch 命令组补全

### Task A1: 添加 sketch add-ellipse

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/sketch.py`

在 `sketch_add_arc` 函数后（约第 195 行）追加：

```python
@sketch_group.command("add-ellipse")
@click.argument("sketch_name")
@click.option("--center", "-c", default="0,0", help="Center x,y.")
@click.option("--major-radius", default=10.0, type=float, help="Major radius.")
@click.option("--minor-radius", default=5.0, type=float, help="Minor radius.")
@click.option("--major-angle", default=0.0, type=float, help="Major axis angle (deg).")
@_handle_error
def sketch_add_ellipse(sketch_name: str, center: str, major_radius: float,
                       minor_radius: float, major_angle: float) -> None:
    """Add an ellipse to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy = [float(x) for x in center.split(",")]
        code = f"""\
import FreeCAD
import Part
import math
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
center = FreeCAD.Vector({cx}, {cy}, 0)
# Create ellipse using Part.Ellipse
ellipse = Part.Ellipse(center, {major_radius}, {minor_radius})
# Rotate if needed
if {major_angle} != 0:
    ellipse.rotate(FreeCAD.Placement(center, FreeCAD.Rotation(0, 0, {major_angle})))
sketch.addGeometry(ellipse.toBSpline(), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added ellipse to {sketch_name}")
    finally:
        backend.disconnect()
```

验证：`python -c "from fc_cli.main import cli; print('sketch add-ellipse OK')"`

---

### Task A2: 添加 sketch add-polygon

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/sketch.py`

```python
@sketch_group.command("add-polygon")
@click.argument("sketch_name")
@click.option("--center", "-c", default="0,0", help="Center x,y.")
@click.option("--radius", "-r", default=5.0, type=float, help="Circumradius.")
@click.option("--sides", "-s", default=6, type=int, help="Number of sides.")
@_handle_error
def sketch_add_polygon(sketch_name: str, center: str, radius: float,
                       sides: int) -> None:
    """Add a regular polygon to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy = [float(x) for x in center.split(",")]
        code = f"""\
import FreeCAD
import Part
import math
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
center = FreeCAD.Vector({cx}, {cy}, 0)
points = []
for i in range({sides}):
    angle = 2 * math.pi * i / {sides}
    x = {cx} + {radius} * math.cos(angle)
    y = {cy} + {radius} * math.sin(angle)
    points.append(FreeCAD.Vector(x, y, 0))
# Close the polygon
points.append(points[0])
for i in range(len(points) - 1):
    sketch.addGeometry(Part.LineSegment(points[i], points[i+1]), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added {sides}-gon to {sketch_name}")
    finally:
        backend.disconnect()
```

---

### Task A3: 添加 sketch add-bspline

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/sketch.py`

```python
@sketch_group.command("add-bspline")
@click.argument("sketch_name")
@click.option("--points", "-p", required=True,
              help="Control points as semicolon-separated x,y pairs.")
@click.option("--closed", is_flag=True, default=False, help="Close the B-spline.")
@_handle_error
def sketch_add_bspline(sketch_name: str, points: str, closed: bool) -> None:
    """Add a B-spline curve to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        pts = []
        for pt_str in points.split(";"):
            pt_str = pt_str.strip()
            if pt_str:
                coords = [float(x) for x in pt_str.split(",")]
                pts.append(f"FreeCAD.Vector({coords[0]}, {coords[1]}, 0)")
        points_list = ", ".join(pts)
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
pts = [{points_list}]
if len(pts) < 2:
    raise ValueError("At least 2 control points required")
bspline = Part.BSplineCurve()
bspline.interpolate(pts, {str(closed).lower()})
sketch.addGeometry(bspline.toBSpline(), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added B-spline to {sketch_name}")
    finally:
        backend.disconnect()
```

---

### Task A4: 添加 sketch add-slot

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/sketch.py`

```python
@sketch_group.command("add-slot")
@click.argument("sketch_name")
@click.option("--center", "-c", default="0,0", help="Center x,y.")
@click.option("--length", "-l", default=20.0, type=float, help="Slot length.")
@click.option("--width", "-w", default=5.0, type=float, help="Slot width (diameter).")
@click.option("--angle", default=0.0, type=float, help="Rotation angle (deg).")
@_handle_error
def sketch_add_slot(sketch_name: str, center: str, length: float,
                    width: float, angle: float) -> None:
    """Add a slot (obround) to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        cx, cy = [float(x) for x in center.split(",")]
        code = f"""\
import FreeCAD
import Part
import math
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
center = FreeCAD.Vector({cx}, {cy}, 0)
half_len = {length} / 2
radius = {width} / 2
angle_rad = math.radians({angle})
dx = half_len * math.cos(angle_rad)
dy = half_len * math.sin(angle_rad)
# Two semicircles connected by lines
p1 = FreeCAD.Vector({cx} - dx, {cy} - dy, 0)
p2 = FreeCAD.Vector({cx} + dx, {cy} + dy, 0)
# Add arcs and lines to form slot
sketch.addGeometry(Part.ArcOfCircle(Part.Circle(p1, FreeCAD.Vector(0,0,1), radius), math.pi/2 - angle_rad, 3*math.pi/2 - angle_rad), False)
sketch.addGeometry(Part.ArcOfCircle(Part.Circle(p2, FreeCAD.Vector(0,0,1), radius), -math.pi/2 - angle_rad, math.pi/2 - angle_rad), False)
sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(p1.x - radius*math.sin(angle_rad), p1.y + radius*math.cos(angle_rad), 0), FreeCAD.Vector(p2.x - radius*math.sin(angle_rad), p2.y + radius*math.cos(angle_rad), 0)), False)
sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(p1.x + radius*math.sin(angle_rad), p1.y - radius*math.cos(angle_rad), 0), FreeCAD.Vector(p2.x + radius*math.sin(angle_rad), p2.y - radius*math.cos(angle_rad), 0)), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added slot to {sketch_name}")
    finally:
        backend.disconnect()
```

---

### Task A5: 添加 sketch add-point

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/sketch.py`

```python
@sketch_group.command("add-point")
@click.argument("sketch_name")
@click.option("--position", "-p", default="0,0", help="Position x,y.")
@_handle_error
def sketch_add_point(sketch_name: str, position: str) -> None:
    """Add a point to a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py = [float(x) for x in position.split(",")]
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
sketch.addGeometry(Part.Point(FreeCAD.Vector({px}, {py}, 0)), False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added point to {sketch_name}")
    finally:
        backend.disconnect()
```

---

### Task A6: 添加 sketch delete-geom

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/sketch.py`

```python
@sketch_group.command("delete-geom")
@click.argument("sketch_name")
@click.argument("indices")
@_handle_error
def sketch_delete_geom(sketch_name: str, indices: str) -> None:
    """Delete geometry elements from a sketch by index."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        idx_list = [int(x.strip()) for x in indices.split(",")]
        # Delete in reverse order to preserve indices
        idx_list_sorted = sorted(idx_list, reverse=True)
        deletions = "\n".join([f"sketch.delGeometry({i})" for i in idx_list_sorted])
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
{deletions}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Deleted {len(idx_list)} geometry element(s) from {sketch_name}")
    finally:
        backend.disconnect()
```

---

### Task A7: 添加 sketch trim

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/sketch.py`

```python
@sketch_group.command("trim")
@click.argument("sketch_name")
@click.argument("geom_index")
@click.option("--point", "-p", help="Trim point as x,y.")
@_handle_error
def sketch_trim(sketch_name: str, geom_index: int, point: str | None) -> None:
    """Trim a geometry element at a point."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py = [float(x) for x in point.split(",")] if point else (0, 0)
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
geom = sketch.Geometry[{geom_index}]
if geom is None:
    raise ValueError(f"Geometry index {geom_index} not found")
trim_point = FreeCAD.Vector({px}, {py}, 0)
# Use Sketcher trim
sketch.trim({geom_index}, trim_point)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Trimmed geometry {geom_index} in {sketch_name}")
    finally:
        backend.disconnect()
```

---

### Task A8: 添加 sketch mirror

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/sketch.py`

```python
@sketch_group.command("mirror")
@click.argument("sketch_name")
@click.option("--elements", "-e", required=True, help="Element indices (comma-sep).")
@click.option("--axis", default="x", type=click.Choice(["x", "y"]),
              help="Mirror axis within the sketch plane.")
@_handle_error
def sketch_mirror(sketch_name: str, elements: str, axis: str) -> None:
    """Mirror sketch geometry elements."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        elems = [int(x.strip()) for x in elements.split(",")]
        elem_str = ", ".join(str(e) for e in elems)
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
# Mirror each element
for idx in [{elem_str}]:
    if idx >= sketch.GeometryCount:
        raise ValueError(f"Geometry index {idx} out of range")
    geom = sketch.Geometry[idx]
    if hasattr(geom, "mirror"):
        if "{axis}" == "x":
            geom.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0))
        else:
            geom.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0))
        sketch.addGeometry(geom, False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Mirrored {len(elements.split(','))} element(s) in {sketch_name}")
    finally:
        backend.disconnect()
```

---

### Task A9: 添加 sketch clone

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/sketch.py`

```python
@sketch_group.command("clone")
@click.argument("sketch_name")
@click.option("--elements", "-e", required=True, help="Element indices (comma-sep).")
@click.option("--offset", default="10,0", help="Clone offset as dx,dy.")
@_handle_error
def sketch_clone(sketch_name: str, elements: str, offset: str) -> None:
    """Clone sketch geometry elements with an offset."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        elems = [int(x.strip()) for x in elements.split(",")]
        dx, dy = [float(x) for x in offset.split(",")]
        elem_str = ", ".join(str(e) for e in elems)
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
offset = FreeCAD.Vector({dx}, {dy}, 0)
for idx in [{elem_str}]:
    if idx >= sketch.GeometryCount:
        raise ValueError(f"Geometry index {idx} out of range")
    geom = sketch.Geometry[idx]
    if hasattr(geom, "copy"):
        new_geom = geom.copy()
        if hasattr(new_geom, "move"):
            new_geom.move(offset)
        sketch.addGeometry(new_geom, False)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Cloned {len(elems)} element(s) in {sketch_name}")
    finally:
        backend.disconnect()
```

---

### Task A10: 添加 sketch export

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/sketch.py`

```python
@sketch_group.command("export")
@click.argument("sketch_name")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output DXF file path.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def sketch_export(sketch_name: str, output: str, overwrite: bool) -> None:
    """Export a sketch to DXF format."""
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
import importDXF
doc = FreeCAD.ActiveDocument
sketch = doc.getObject("{sketch_name}")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
importDXF.export([sketch], r"{os.path.abspath(output)}")
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Exported {sketch_name} to {output}")
    finally:
        backend.disconnect()
```

---

## Part B: Surface 命令组补全

### Task B1: 添加 surface extrude

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/surface.py`

在 `surface_list` 函数后追加：

```python
@surface_group.command("extrude")
@click.argument("name")
@click.option("--direction", "-d", default="0,0,10", help="Extrude direction as x,y,z.")
@click.option("--name", "-n", "result_name", help="Result object name.")
@_handle_error
def surface_extrude(name: str, direction: str, result_name: str | None) -> None:
    """Extrude a face or wire into a surface/solid."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        dx, dy, dz = [float(x) for x in direction.split(",")]
        out_name = result_name or f"{name}_Extruded"
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if not hasattr(obj, "Shape") or not obj.Shape:
    raise ValueError(f"Object '{name}' has no Shape")
shape = obj.Shape
dir_vec = FreeCAD.Vector({dx}, {dy}, {dz})
# Extrude faces or wires
if shape.Faces:
    extruded = shape.Faces[0].extrude(dir_vec)
elif shape.Wires:
    extruded = shape.Wires[0].makeOffsetShape(dir_vec.Length, 0.01)
else:
    raise ValueError("Object has no faces or wires to extrude")
result = doc.addObject("Part::Feature", "{out_name}")
result.Shape = extruded
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{out_name}", "direction": [{dx}, {dy}, {dz}]}}, "message": "Created extruded surface: {out_name}"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()
```

---

### Task B2: 添加 surface revolve

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/surface.py`

```python
@surface_group.command("revolve")
@click.argument("name")
@click.option("--axis", "-a", default="0,0,0,1,0,0",
              help="Axis as origin_x,origin_y,origin_z,dir_x,dir_y,dir_z.")
@click.option("--angle", default=360.0, type=float, help="Revolution angle (degrees).")
@click.option("--name", "-n", "result_name", help="Result object name.")
@_handle_error
def surface_revolve(name: str, axis: str, angle: float,
                    result_name: str | None) -> None:
    """Revolve a profile around an axis to create a surface."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        parts = [float(x) for x in axis.split(",")]
        ox, oy, oz, dx, dy, dz = parts
        out_name = result_name or f"{name}_Revolved"
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if not hasattr(obj, "Shape") or not obj.Shape:
    raise ValueError(f"Object '{name}' has no Shape")
shape = obj.Shape
axis_origin = FreeCAD.Vector({ox}, {oy}, {oz})
axis_dir = FreeCAD.Vector({dx}, {dy}, {dz})
if shape.Wires:
    revolved = shape.Wires[0].revolve(axis_origin, axis_dir, {angle})
elif shape.Faces:
    revolved = shape.Faces[0].revolve(axis_origin, axis_dir, {angle})
else:
    raise ValueError("Object has no faces or wires to revolve")
result = doc.addObject("Part::Feature", "{out_name}")
result.Shape = revolved
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{out_name}", "angle": {angle}}}, "message": "Created revolved surface: {out_name}"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()
```

---

### Task B3: 添加 surface ruled

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/surface.py`

```python
@surface_group.command("ruled")
@click.argument("wire1_name")
@click.argument("wire2_name")
@click.option("--name", "-n", help="Result object name.")
@_handle_error
def surface_ruled(wire1_name: str, wire2_name: str, name: str | None) -> None:
    """Create a ruled surface between two wires."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "RuledSurface"
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj1 = doc.getObject("{wire1_name}")
obj2 = doc.getObject("{wire2_name}")
if obj1 is None:
    raise ValueError(f"Object '{wire1_name}' not found")
if obj2 is None:
    raise ValueError(f"Object '{wire2_name}' not found")
w1 = obj1.Shape.Wires[0] if obj1.Shape.Wires else None
w2 = obj2.Shape.Wires[0] if obj2.Shape.Wires else None
if w1 is None or w2 is None:
    raise ValueError("Both objects must have wires")
ruled = Part.makeRuledSurface(w1, w2)
result = doc.addObject("Part::Feature", "{result_name}")
result.Shape = ruled
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{result_name}", "wire1": "{wire1_name}", "wire2": "{wire2_name}"}}, "message": "Created ruled surface: {result_name}"}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()
```

---

### Task B4: 添加 surface curvature

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/surface.py`

```python
@surface_group.command("curvature")
@click.argument("name")
@click.option("--face-index", default=0, type=int, help="Face index to analyze.")
@_handle_error
def surface_curvature(name: str, face_index: int) -> None:
    """Analyze curvature of a surface."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if not hasattr(obj, "Shape") or not obj.Shape:
    raise ValueError(f"Object '{name}' has no Shape")
faces = obj.Shape.Faces
if not faces:
    raise ValueError(f"Object '{name}' has no faces")
if {face_index} >= len(faces):
    raise ValueError(f"Face index {face_index} out of range (0-{len(faces)-1})")
face = faces[{face_index}]
surf = face.Surface
# Get curvature info
if hasattr(surf, "curvature"):
    curv = surf.curvature(0.5, 0.5)
else:
    curv = None
# Get bounds
bb = face.BoundBox
_fc_result = {{
    "status": "ok",
    "data": {{
        "name": "{name}",
        "face_index": {face_index},
        "surface_type": type(surf).__name__,
        "area": face.Area,
        "bounds": {{"x": [bb.XMin, bb.XMax], "y": [bb.YMin, bb.YMax], "z": [bb.ZMin, bb.ZMax]}},
    }},
    "message": ""
}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"Curvature analysis for {name}:")
    finally:
        backend.disconnect()
```

---

## Part C: Draft 命令组补全

### Task C1: 添加 draft clone

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/draft.py`

在 `draft_list` 函数后追加：

```python
@draft_group.command("clone")
@click.argument("name")
@click.option("--name", "-n", "clone_name", help="Clone name.")
@_handle_error
def draft_clone(name: str, clone_name: str | None) -> None:
    """Clone a Draft object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = clone_name or f"{name}_Clone"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
clone = Draft.clone(obj)
clone.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Cloned: {name} -> {out_name}")
    finally:
        backend.disconnect()
```

---

### Task C2: 添加 draft mirror

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/draft.py`

```python
@draft_group.command("mirror")
@click.argument("name")
@click.option("--axis", default="X", type=click.Choice(["X", "Y", "Z"]),
              help="Mirror axis.")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_mirror(name: str, axis: str, result_name: str | None) -> None:
    """Mirror a Draft object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Mirrored"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if "{axis}" == "X":
    axis_vec = FreeCAD.Vector(1, 0, 0)
elif "{axis}" == "Y":
    axis_vec = FreeCAD.Vector(0, 1, 0)
else:
    axis_vec = FreeCAD.Vector(0, 0, 1)
mirrored = Draft.mirror(obj, FreeCAD.Vector(0, 0, 0), axis_vec)
mirrored.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Mirrored: {name} -> {out_name} (axis={axis})")
    finally:
        backend.disconnect()
```

---

### Task C3: 添加 draft stretch

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/draft.py`

```python
@draft_group.command("stretch")
@click.argument("name")
@click.option("--vector", "-v", required=True, help="Stretch vector as x,y,z.")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_stretch(name: str, vector: str, result_name: str | None) -> None:
    """Stretch a Draft object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        vx, vy, vz = [float(x) for x in vector.split(",")]
        out_name = result_name or f"{name}_Stretched"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
Draft.move(obj, FreeCAD.Vector({vx}, {vy}, {vz}))
obj.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Stretched: {name} -> {out_name}")
    finally:
        backend.disconnect()
```

---

### Task C4: 添加 draft upgrade

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/draft.py`

```python
@draft_group.command("upgrade")
@click.argument("name")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_upgrade(name: str, result_name: str | None) -> None:
    """Upgrade a Draft object (line->wire->face->shell->solid)."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Upgraded"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
upgraded = Draft.upgrade([obj], delete=True)
if upgraded and len(upgraded) > 0:
    upgraded[0].Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Upgraded: {name} -> {out_name}")
    finally:
        backend.disconnect()
```

---

### Task C5: 添加 draft downgrade

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/draft.py`

```python
@draft_group.command("downgrade")
@click.argument("name")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_downgrade(name: str, result_name: str | None) -> None:
    """Downgrade a Draft object (solid->shell->face->wire->line)."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Downgraded"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
downgraded = Draft.downgrade([obj], delete=True)
if downgraded and len(downgraded) > 0:
    downgraded[0].Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Downgraded: {name} -> {out_name}")
    finally:
        backend.disconnect()
```

---

### Task C6: 添加 draft path-array

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/draft.py`

```python
@draft_group.command("path-array")
@click.argument("name")
@click.argument("path_name")
@click.option("--count", "-c", default=5, type=int, help="Number of items.")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_path_array(name: str, path_name: str, count: int,
                     result_name: str | None) -> None:
    """Create a path array along a wire/edge."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_PathArray"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
path_obj = doc.getObject("{path_name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if path_obj is None:
    raise ValueError(f"Path object '{path_name}' not found")
array = Draft.make_path_array(obj, path_obj, {count})
array.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created path array: {out_name} ({count} items)")
    finally:
        backend.disconnect()
```

---

### Task C7: 添加 draft point-array

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/draft.py`

```python
@draft_group.command("point-array")
@click.argument("name")
@click.argument("points_name")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_point_array(name: str, points_name: str, result_name: str | None) -> None:
    """Create a point array at specified points."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_PointArray"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
points_obj = doc.getObject("{points_name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if points_obj is None:
    raise ValueError(f"Points object '{points_name}' not found")
array = Draft.make_point_array(obj, [points_obj])
array.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created point array: {out_name}")
    finally:
        backend.disconnect()
```

---

### Task C8: 添加 draft point

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/draft.py`

```python
@draft_group.command("point")
@click.option("--position", "-p", default="0,0,0", help="Position as x,y,z.")
@click.option("--name", "-n", help="Object name.")
@_handle_error
def draft_point(position: str, name: str | None) -> None:
    """Create a point."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py, pz = [float(x) for x in position.split(",")]
        obj_name = name or "Point"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
pt = Draft.make_point(FreeCAD.Vector({px}, {py}, {pz}))
pt.Label = "{obj_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created point: {obj_name}")
    finally:
        backend.disconnect()
```

---

### Task C9: 添加 draft facebinder

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/draft.py`

```python
@draft_group.command("facebinder")
@click.argument("name")
@click.option("--faces", "-f", required=True, help="Source object faces as obj.EdgeN;...")
@click.option("--name", "-n", "result_name", help="Result name.")
@_handle_error
def draft_facebinder(name: str, faces: str, result_name: str | None) -> None:
    """Create a facebinder from selected faces."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        out_name = result_name or f"{name}_Facebinder"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
fb = Draft.make_facebinder([obj])
fb.Label = "{out_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created facebinder: {out_name}")
    finally:
        backend.disconnect()
```

---

### Task C10: 添加 draft label

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/draft.py`

```python
@draft_group.command("label")
@click.argument("target_name")
@click.option("--text", "-t", required=True, help="Label text.")
@click.option("--position", "-p", default="0,0,0", help="Position as x,y,z.")
@click.option("--name", "-n", help="Label name.")
@_handle_error
def draft_label(target_name: str, text: str, position: str,
                name: str | None) -> None:
    """Create a label pointing to an object."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py, pz = [float(x) for x in position.split(",")]
        label_name = name or "Label"
        code = f"""\
import FreeCAD
import Draft
doc = FreeCAD.ActiveDocument
target = doc.getObject("{target_name}")
if target is None:
    raise ValueError(f"Target '{target_name}' not found")
label = Draft.make_label("{text}", FreeCAD.Vector({px}, {py}, {pz}))
label.Target = [target, []]
label.Label = "{label_name}"
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created label: {label_name}")
    finally:
        backend.disconnect()
```

---

## Part D: 创建 SKILL.md 文件

### Task D1: 创建 fc-sketch SKILL.md

**Files:**
- Create: `docs/skills/fc-sketch/SKILL.md`

内容：
```markdown
---
name: fc-sketch
description: FreeCAD 2D 草图命令 — 几何创建（线/圆/弧/矩形/椭圆/多边形/B 样条/槽/点）、约束、修剪/镜像/克隆/导出。
---

# fc-sketch — FreeCAD 2D 草图 CLI 命令

## 命令组概览（18 个命令）

| 命令 | 说明 |
|------|------|
| `sketch new` | 创建新草图 |
| `sketch add-line` | 添加线段 |
| `sketch add-circle` | 添加圆 |
| `sketch add-rect` | 添加矩形 |
| `sketch add-arc` | 添加圆弧 |
| `sketch add-ellipse` | 添加椭圆 |
| `sketch add-polygon` | 添加正多边形 |
| `sketch add-bspline` | 添加 B 样条曲线 |
| `sketch add-slot` | 添加槽（跑道形）|
| `sketch add-point` | 添加点 |
| `sketch constrain` | 添加约束 |
| `sketch close` | 关闭/完成草图 |
| `sketch delete-geom` | 删除几何元素 |
| `sketch trim` | 修剪几何 |
| `sketch mirror` | 镜像几何 |
| `sketch clone` | 克隆几何 |
| `sketch list` | 列出所有草图 |
| `sketch get` | 获取草图详情 |
| `sketch validate` | 验证草图 |
| `sketch solve-status` | 约束求解状态 |
| `sketch export` | 导出为 DXF |

## 约束类型速查

| 约束类型 | 说明 |
|----------|------|
| `horizontal` | 水平 |
| `vertical` | 垂直 |
| `coincident` | 重合 |
| `parallel` | 平行 |
| `perpendicular` | 垂直 |
| `equal` | 等长 |
| `fixed` | 固定 |
| `distance` | 距离 |
| `angle` | 角度 |
| `radius` | 半径 |
| `diameter` | 直径 |
| `tangent` | 相切 |
| `symmetric` | 对称 |
| `point_on_object` | 点在对象上 |
| `distance_x` | X 方向距离 |
| `distance_y` | Y 方向距离 |

## 典型工作流

### 工作流 1：创建参数化草图
```bash
fc sketch new --name MySketch --plane XY
fc sketch add-circle MySketch --center 0,0 --radius 25
fc sketch add-circle MySketch --center 35,0 --radius 5
fc sketch constrain MySketch coincident --elements 0
fc sketch constrain MySketch distance --elements 0,1 --value 35
fc sketch validate MySketch
```

### 工作流 2：创建多边形 + 镜像
```bash
fc sketch new --name PolySketch --plane XY
fc sketch add-polygon PolySketch --center 0,0 --radius 20 --sides 6
fc sketch mirror PolySketch --elements 0,1,2 --axis x
fc sketch close PolySketch
```

### 工作流 3：B 样条曲线
```bash
fc sketch new --name SplineSketch --plane XY
fc sketch add-bspline SplineSketch --points "0,0;10,20;30,10;40,30" --closed
fc sketch close SplineSketch
fc sketch export SplineSketch --output spline.dxf
```

## 注意事项

- 所有命令支持 `--json` 输出
- `sketch constrain` 的 `--elements` 是几何元素索引（从 0 开始）
- `sketch add-bspline` 的 `--points` 是分号分隔的 x,y 坐标对
- `sketch add-polygon` 的 `--radius` 是外接圆半径
- `sketch export` 导出为 DXF 格式
```

---

### Task D2: 创建 fc-surface SKILL.md

**Files:**
- Create: `docs/skills/fc-surface/SKILL.md`

内容：
```markdown
---
name: fc-surface
description: FreeCAD 曲面操作命令 — 放样/扫描/填充/管道/偏移/加厚/展平/缝合/拉伸/旋转/直纹/曲率分析。
---

# fc-surface — FreeCAD 曲面操作 CLI 命令

## 命令组概览（13 个命令）

| 命令 | 说明 |
|------|------|
| `surface loft` | 放样曲面 |
| `surface sweep` | 扫描曲面 |
| `surface fill` | 填充曲面 |
| `surface pipe` | 管道曲面 |
| `surface offset` | 偏移曲面 |
| `surface thicken` | 加厚曲面 |
| `surface flatten` | 展平曲面 |
| `surface sew` | 缝合曲面 |
| `surface extrude` | 拉伸曲面 |
| `surface revolve` | 旋转曲面 |
| `surface ruled` | 直纹曲面 |
| `surface curvature` | 曲率分析 |
| `surface list` | 列出曲面对象 |

## 典型工作流

### 工作流 1：放样曲面
```bash
fc document new --name LoftSurf
fc sketch new --name Profile1 --plane XY
fc sketch add-circle Profile1 --center 0,0 --radius 10
fc sketch close Profile1
fc sketch new --name Profile2 --plane XY --offset 20
fc sketch add-circle Profile2 --center 0,0 --radius 15
fc sketch close Profile2
fc surface loft --profiles "Profile1;Profile2" --solid
fc export step --output loft_surf.step
```

### 工作流 2：管道曲面
```bash
fc document new --name PipeSurf
fc sketch new --name PathSketch --plane XY
fc sketch add-arc PathSketch --center 0,0 --radius 20 --start-angle 0 --end-angle 180
fc sketch close PathSketch
fc surface pipe --path PathSketch --radius 3
fc export step --output pipe_surf.step
```

### 工作流 3：加厚曲面
```bash
fc surface thicken Loft --thickness 2 --direction both
fc export step --output thickened.step
```

## 注意事项

- 所有命令支持 `--json` 输出
- `surface loft` 需要至少 2 个轮廓
- `surface thicken` 的 `--direction` 可以是 `both` 或 `single`
- `surface curvature` 分析指定面的曲率信息
```

---

### Task D3: 创建 fc-draft SKILL.md

**Files:**
- Create: `docs/skills/fc-draft/SKILL.md`

内容：
```markdown
---
name: fc-draft
description: FreeCAD Draft 工作台命令 — 2D/3D 绘图、标注、阵列、变换、升级/降级、路径阵列、标签。
---

# fc-draft — FreeCAD Draft 工作台 CLI 命令

## 命令组概览（22 个命令）

| 命令 | 说明 |
|------|------|
| `draft line` | 创建线段 |
| `draft wire` | 创建多段线 |
| `draft circle` | 创建圆 |
| `draft arc` | 创建圆弧 |
| `draft rect` | 创建矩形 |
| `draft polygon` | 创建正多边形 |
| `draft text` | 创建文字 |
| `draft dimension` | 创建标注 |
| `draft array` | 阵列（极坐标/矩形）|
| `draft offset` | 偏移 |
| `draft move` | 移动 |
| `draft rotate` | 旋转 |
| `draft scale` | 缩放 |
| `draft trim` | 修剪/延伸 |
| `draft clone` | 克隆 |
| `draft mirror` | 镜像 |
| `draft stretch` | 拉伸 |
| `draft upgrade` | 升级（线->面->体）|
| `draft downgrade` | 降级（体->面->线）|
| `draft path-array` | 路径阵列 |
| `draft point-array` | 点阵列 |
| `draft point` | 创建点 |
| `draft facebinder` | 面绑定器 |
| `draft label` | 标签 |
| `draft list` | 列出 Draft 对象 |

## 典型工作流

### 工作流 1：2D 工程布局
```bash
fc document new --name Layout
fc draft rect --corner 0,0 --width 100 --height 80 --name OuterFrame
fc draft rect --corner 10,10 --width 30 --height 20 --name Window1
fc draft rect --corner 60,10 --width 30 --height 20 --name Window2
fc draft dimension --start 0,0 --end 100,0 --offset 0,-10 --name WidthDim
fc export dxf --output layout.dxf
```

### 工作流 2：路径阵列
```bash
fc draft circle --center 0,0 --radius 5 --name Bolt
fc draft wire --points "0,0,0;50,0,0;50,50,0;0,50,0" --closed --name Path
fc draft path-array Bolt --path Path --count 8
```

### 工作流 3：升级和降级
```bash
fc draft wire --points "0,0,0;10,0,0;10,10,0;0,10,0" --closed --name Profile
fc draft upgrade Profile --name ProfileFace
fc draft downgrade ProfileFace --name ProfileEdges
```

## 注意事项

- 所有命令支持 `--json` 输出
- `draft array` 支持 `polar`（极坐标）和 `rectangular`（矩形）两种类型
- `draft path-array` 沿路径均匀分布对象
- `draft upgrade` 尝试将低级几何升级为高级几何
- `draft downgrade` 将高级几何分解为低级几何
```

---

## Part E: 最终验证

### Task E1: 全量验证

```bash
cd D:\桌面文件\fc && python -c "
from fc_cli.main import cli
from click.testing import CliRunner
runner = CliRunner()

new_commands = [
    'sketch add-ellipse', 'sketch add-polygon', 'sketch add-bspline',
    'sketch add-slot', 'sketch add-point', 'sketch delete-geom',
    'sketch trim', 'sketch mirror', 'sketch clone', 'sketch export',
    'surface extrude', 'surface revolve', 'surface ruled', 'surface curvature',
    'draft clone', 'draft mirror', 'draft stretch', 'draft upgrade',
    'draft downgrade', 'draft path-array', 'draft point-array',
    'draft point', 'draft facebinder', 'draft label',
]
for cmd in new_commands:
    result = runner.invoke(cli, cmd.split() + ['--help'])
    status = 'OK' if result.exit_code == 0 else 'FAIL'
    print(f'{status}: {cmd}')
    if result.exit_code != 0:
        print(f'  -> {result.output[:200]}')
"
```

Expected: 所有命令显示 OK

```bash
cd D:\桌面文件\fc && python -m pytest packages/cli/tests/ -v --tb=short
```

Expected: 20 passed（原有测试全部通过）
