# Batch 1: Part 3D 基元补全 + PartDesign 高级特征 + Skills

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补全 Part 命令组缺失的 3D 基元类型（ellipsoid、spiral、thread 等），补全 PartDesign Body 缺失的高级特征（阵列、孔、抽壳、拔模、基准特征等），创建 `fc-part` 和 `fc-part-design` 两个 SKILL.md。

**Architecture:** 在现有 `part.py` 和 `body.py` 文件中追加新命令函数，遵循 `_get_backend()` + `_handle_error` + `execute_code()` 模式。每个新命令 ~30-50 行。SKILL.md 放在 `docs/skills/` 下独立子目录中。

**Tech Stack:** Python 3.13, Click, fc-core (HeadlessBackend/RPCBackend), FreeCAD API via execute_code

---

## Part A: Part 命令组补全

### Task A1: 补全 part add 缺失的 3D 基元类型

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/part.py:72-80` (type_map 字典)

当前 `part add` 的 `type_map` 缺少 `ellipsoid`、`spiral`、`thread`。需要扩展 type_map 和默认参数。

- [ ] **Step 1: 修改 part.py 的 type_map 和默认参数**

在 `part_add` 函数中，找到 `type_map` 字典（约第 72-80 行），扩展为：

```python
        type_map = {
            "box": "Part::Box",
            "cylinder": "Part::Cylinder",
            "sphere": "Part::Sphere",
            "cone": "Part::Cone",
            "torus": "Part::Torus",
            "wedge": "Part::Wedge",
            "helix": "Part::Helix",
            "ellipsoid": "Part::Ellipsoid",
            "spiral": "Part::Spiral",
        }
```

同时在默认 props 部分（约第 93-102 行）追加：

```python
        elif part_type == "ellipsoid" and not props:
            props = {"Radius1": 10, "Radius2": 5, "Radius3": 3}
```

- [ ] **Step 2: 更新 part add 的 docstring**

将 docstring 中 `Supported types` 行更新为：
```python
    """Add a 3D primitive part.

    Supported types: box, cylinder, sphere, cone, torus, wedge, helix, ellipsoid, spiral.
    """
```

- [ ] **Step 3: 验证**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('part OK')"
python -m fc_cli.main part add --help
```

Expected: 无报错，help 显示正确

- [ ] **Step 4: Commit**

```bash
git add packages/cli/src/fc_cli/commands/part.py
git commit -m "feat(part): add ellipsoid and spiral primitive types"
```

---

### Task A2: 添加 part hole 命令

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/part.py` (文件末尾追加)

- [ ] **Step 1: 在 part.py 末尾追加 part hole 命令**

在 `part_bounds` 函数后追加：

```python
@part_group.command("hole")
@click.argument("name")
@click.option("--diameter", "-d", default=5.0, type=float, help="Hole diameter.")
@click.option("--depth", default=10.0, type=float, help="Hole depth.")
@click.option("--position", "-pos", help="Position as x,y,z.")
@click.option("--direction", default="0,0,1", help="Hole direction as x,y,z.")
@click.option("--name", "-n", "result_name", help="Name for result.")
@_handle_error
def part_hole(name: str, diameter: float, depth: float,
              position: str | None, direction: str,
              result_name: str | None) -> None:
    """Create a hole through a part."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        dx, dy, dz = [float(x) for x in direction.split(",")]
        px, py, pz = [float(x) for x in position.split(",")] if position else (0, 0, 0)
        out_name = result_name or f"{name}_Hole"
        radius = diameter / 2.0
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{name}")
if obj is None:
    raise ValueError(f"Object '{name}' not found")
if not hasattr(obj, "Shape") or not obj.Shape:
    raise ValueError(f"Object '{name}' has no Shape")
# Create a cylinder for the hole
hole_cyl = Part.makeCylinder({radius}, {depth}, FreeCAD.Vector({px}, {py}, {pz}), FreeCAD.Vector({dx}, {dy}, {dz}))
result = doc.addObject("Part::Feature", "{out_name}")
result.Shape = obj.Shape.cut(hole_cyl)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created hole: {out_name} (⌀{diameter}mm)")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证导入**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('part hole OK')"
```

Expected: 无报错

- [ ] **Step 3: Commit**

```bash
git add packages/cli/src/fc_cli/commands/part.py
git commit -m "feat(part): add part hole command"
```

---

## Part B: PartDesign Body 命令组补全

### Task B1: 添加 body pattern-linear（线性阵列）

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/body.py` (body_get 函数后追加)

- [ ] **Step 1: 在 body.py 末尾追加 body pattern-linear 命令**

```python
@body_group.command("pattern-linear")
@click.argument("body_name")
@click.argument("feature_name")
@click.option("--direction", "-d", default="X", type=click.Choice(["X", "Y", "Z"]),
              help="Pattern direction.")
@click.option("--count", "-c", default=3, type=int, help="Number of instances.")
@click.option("--spacing", "-s", default=10.0, type=float, help="Spacing between instances.")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_pattern_linear(body_name: str, feature_name: str, direction: str,
                        count: int, spacing: float, name: str | None) -> None:
    """Create a linear pattern of a feature in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or f"{feature_name}_LinearPattern"
        axis_vec = {"X": "1,0,0", "Y": "0,1,0", "Z": "0,0,1"}[direction]
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
feature = body.getObject("{feature_name}")
if feature is None:
    raise ValueError(f"Feature '{feature_name}' not found in body '{body_name}'")
pattern = body.newObject("PartDesign::LinearPattern", "{result_name}")
pattern.Originals = [feature]
pattern.Direction = (feature, ['{direction}Axis'])
pattern.Length = {spacing * (count - 1)}
pattern.Occurrences = {count}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created linear pattern: {result_name} ({count}x {direction})")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证导入**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('body pattern-linear OK')"
```

- [ ] **Step 3: Commit**

```bash
git add packages/cli/src/fc_cli/commands/body.py
git commit -m "feat(body): add body pattern-linear command"
```

---

### Task B2: 添加 body pattern-polar（圆周阵列）

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/body.py` (body_pattern_linear 后追加)

- [ ] **Step 1: 追加 body pattern-polar 命令**

```python
@body_group.command("pattern-polar")
@click.argument("body_name")
@click.argument("feature_name")
@click.option("--axis", "-a", default="Z", type=click.Choice(["X", "Y", "Z"]),
              help="Rotation axis.")
@click.option("--count", "-c", default=6, type=int, help="Number of instances.")
@click.option("--angle", default=360.0, type=float, help="Total angle (degrees).")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_pattern_polar(body_name: str, feature_name: str, axis: str,
                       count: int, angle: float, name: str | None) -> None:
    """Create a polar (circular) pattern of a feature in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or f"{feature_name}_PolarPattern"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
feature = body.getObject("{feature_name}")
if feature is None:
    raise ValueError(f"Feature '{feature_name}' not found in body '{body_name}'")
pattern = body.newObject("PartDesign::PolarPattern", "{result_name}")
pattern.Originals = [feature]
pattern.Axis = (feature, ['{axis}Axis'])
pattern.Angle = {angle}
pattern.Occurrences = {count}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created polar pattern: {result_name ({count}x {angle}°)")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证 + Commit**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('body pattern-polar OK')"
git add packages/cli/src/fc_cli/commands/body.py
git commit -m "feat(body): add body pattern-polar command"
```

---

### Task B3: 添加 body pattern-mirror（镜像特征）

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/body.py`

- [ ] **Step 1: 追加 body pattern-mirror 命令**

```python
@body_group.command("pattern-mirror")
@click.argument("body_name")
@click.argument("feature_name")
@click.option("--plane", "-p", default="XY", type=click.Choice(["XY", "XZ", "YZ"]),
              help="Mirror plane.")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_pattern_mirror(body_name: str, feature_name: str, plane: str,
                        name: str | None) -> None:
    """Create a mirrored pattern of a feature in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or f"{feature_name}_MirrorPattern"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
feature = body.getObject("{feature_name}")
if feature is None:
    raise ValueError(f"Feature '{feature_name}' not found in body '{body_name}'")
pattern = body.newObject("PartDesign::MirroredPattern", "{result_name}")
pattern.Originals = [feature]
pattern.MirrorPlane = (feature, ['{plane}Plane'])
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created mirror pattern: {result_name} (plane={plane})")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证 + Commit**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('body pattern-mirror OK')"
git add packages/cli/src/fc_cli/commands/body.py
git commit -m "feat(body): add body pattern-mirror command"
```

---

### Task B4: 添加 body hole（孔特征）

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/body.py`

- [ ] **Step 1: 追加 body hole 命令**

```python
@body_group.command("hole")
@click.argument("body_name")
@click.argument("sketch_name")
@click.option("--type", "hole_type", default="simple",
              type=click.Choice(["simple", "counterbore", "countersink", "threaded"]),
              help="Hole type.")
@click.option("--diameter", "-d", default=5.0, type=float, help="Hole diameter.")
@click.option("--depth", default=10.0, type=float, help="Hole depth.")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_hole(body_name: str, sketch_name: str, hole_type: str,
              diameter: float, depth: float, name: str | None) -> None:
    """Add a hole feature to a body based on a sketch."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "Hole"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
sketch = doc.getObject("{sketch_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
if sketch is None:
    raise ValueError(f"Sketch '{sketch_name}' not found")
hole = body.newObject("PartDesign::Hole", "{result_name}")
hole.Profile = sketch
hole.Diameter = {diameter}
hole.Depth = {depth}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created hole: {result_name} (⌀{diameter}mm, type={hole_type})")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证 + Commit**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('body hole OK')"
git add packages/cli/src/fc_cli/commands/body.py
git commit -m "feat(body): add body hole command"
```

---

### Task B5: 添加 body shell（抽壳）

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/body.py`

- [ ] **Step 1: 追加 body shell 命令**

```python
@body_group.command("shell")
@click.argument("body_name")
@click.option("--thickness", "-t", default=2.0, type=float, help="Shell thickness.")
@click.option("--faces", "-f", help="Faces to remove as comma-sep indices.")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_shell(body_name: str, thickness: float, faces: str | None,
               name: str | None) -> None:
    """Create a shell (hollow) from a solid body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "Shell"
        face_list = f"[{faces}]" if faces else "None"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
shell = body.newObject("PartDesign::Thickness", "{result_name}")
shell.Base = (body, {face_list})
shell.Value = {thickness}
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created shell: {result_name} (thickness={thickness}mm)")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证 + Commit**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('body shell OK')"
git add packages/cli/src/fc_cli/commands/body.py
git commit -m "feat(body): add body shell command"
```

---

### Task B6: 添加 body draft（拔模斜度）

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/body.py`

- [ ] **Step 1: 追加 body draft 命令**

```python
@body_group.command("draft")
@click.argument("body_name")
@click.option("--angle", "-a", default=5.0, type=float, help="Draft angle (degrees).")
@click.option("--faces", "-f", required=True, help="Faces as comma-sep indices.")
@click.option("--plane", "-p", default="XY", type=click.Choice(["XY", "XZ", "YZ"]),
              help="Neutral plane.")
@click.option("--name", "-n", help="Result feature name.")
@_handle_error
def body_draft(body_name: str, angle: float, faces: str,
               plane: str, name: str | None) -> None:
    """Add a draft angle to selected faces of a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        result_name = name or "Draft"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
draft = body.newObject("PartDesign::Draft", "{result_name}")
draft.Base = (body, [{faces}])
draft.Angle = {angle}
draft.NeutralPlane = (body, ['{plane}Plane'])
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created draft: {result_name} (angle={angle}°)")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证 + Commit**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('body draft OK')"
git add packages/cli/src/fc_cli/commands/body.py
git commit -m "feat(body): add body draft command"
```

---

### Task B7: 添加 body datum-plane（基准面）

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/body.py`

- [ ] **Step 1: 追加 body datum-plane 命令**

```python
@body_group.command("datum-plane")
@click.argument("body_name")
@click.option("--name", "-n", default="DatumPlane", help="Datum plane name.")
@click.option("--plane", "-p", default="XY", type=click.Choice(["XY", "XZ", "YZ"]),
              help="Reference plane.")
@click.option("--offset", default=0.0, type=float, help="Offset from reference plane.")
@click.option("--rotation", default="0,0,0", help="Rotation as rx,ry,rz degrees.")
@_handle_error
def body_datum_plane(body_name: str, name: str, plane: str,
                     offset: float, rotation: str) -> None:
    """Create a datum (reference) plane in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        rx, ry, rz = [float(x) for x in rotation.split(",")]
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
datum = body.newObject("PartDesign::Plane", "{name}")
datum.Placement = FreeCAD.Placement(FreeCAD.Vector(0, 0, {offset}), FreeCAD.Rotation({rx}, {ry}, {rz}))
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created datum plane: {name} (offset={offset}mm)")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证 + Commit**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('body datum-plane OK')"
git add packages/cli/src/fc_cli/commands/body.py
git commit -m "feat(body): add body datum-plane command"
```

---

### Task B8: 添加 body datum-point（基准点）

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/body.py`

- [ ] **Step 1: 追加 body datum-point 命令**

```python
@body_group.command("datum-point")
@click.argument("body_name")
@click.option("--name", "-n", default="DatumPoint", help="Datum point name.")
@click.option("--position", "-pos", default="0,0,0", help="Position as x,y,z.")
@_handle_error
def body_datum_point(body_name: str, name: str, position: str) -> None:
    """Create a datum (reference) point in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py, pz = [float(x) for x in position.split(",")]
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
datum = body.newObject("PartDesign::Point", "{name}")
datum.Placement = FreeCAD.Placement(FreeCAD.Vector({px}, {py}, {pz}), FreeCAD.Rotation())
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created datum point: {name} at ({px},{py},{pz})")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证 + Commit**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('body datum-point OK')"
git add packages/cli/src/fc_cli/commands/body.py
git commit -m "feat(body): add body datum-point command"
```

---

### Task B9: 添加 body datum-line（基准线）

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/body.py`

- [ ] **Step 1: 追加 body datum-line 命令**

```python
@body_group.command("datum-line")
@click.argument("body_name")
@click.option("--name", "-n", default="DatumLine", help="Datum line name.")
@click.option("--direction", "-d", default="Z", type=click.Choice(["X", "Y", "Z"]),
              help="Line direction.")
@click.option("--position", "-pos", default="0,0,0", help="Position as x,y,z.")
@_handle_error
def body_datum_line(body_name: str, name: str, direction: str, position: str) -> None:
    """Create a datum (reference) line in a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        px, py, pz = [float(x) for x in position.split(",")]
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
datum = body.newObject("PartDesign::Line", "{name}")
datum.Placement = FreeCAD.Placement(FreeCAD.Vector({px}, {py}, {pz}), FreeCAD.Rotation())
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created datum line: {name} (dir={direction})")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证 + Commit**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('body datum-line OK')"
git add packages/cli/src/fc_cli/commands/body.py
git commit -m "feat(body): add body datum-line command"
```

---

### Task B10: 添加 body set-tip（设置建模位置）

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/body.py`

- [ ] **Step 1: 追加 body set-tip 命令**

```python
@body_group.command("set-tip")
@click.argument("body_name")
@click.option("--feature", "-f", help="Feature name to set as tip. Empty = reset to last.")
@_handle_error
def body_set_tip(body_name: str, feature: str | None) -> None:
    """Set the tip (current modeling position) of a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        if feature:
            code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
feat = body.getObject("{feature}")
if feat is None:
    raise ValueError(f"Feature '{feature}' not found in body '{body_name}'")
body.Tip = feat
doc.recompute()
"""
        else:
            code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
if body.Group:
    body.Tip = body.Group[-1]
doc.recompute()
"""
        r = backend.execute_code(code)
        tip_name = feature or "last feature"
        _output.output(r.to_dict(), r.message or f"Set tip of '{body_name}' to '{tip_name}'")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证 + Commit**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('body set-tip OK')"
git add packages/cli/src/fc_cli/commands/body.py
git commit -m "feat(body): add body set-tip command"
```

---

### Task B11: 添加 body remove-feature（移除特征）

**Files:**
- Modify: `packages/cli/src/fc_cli/commands/body.py`

- [ ] **Step 1: 追加 body remove-feature 命令**

```python
@body_group.command("remove-feature")
@click.argument("body_name")
@click.argument("feature_name")
@_handle_error
def body_remove_feature(body_name: str, feature_name: str) -> None:
    """Remove a feature from a body."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
body = doc.getObject("{body_name}")
if body is None:
    raise ValueError(f"Body '{body_name}' not found")
feat = body.getObject("{feature_name}")
if feat is None:
    raise ValueError(f"Feature '{feature_name}' not found in body '{body_name}'")
body.removeObject(feat)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Removed feature '{feature_name}' from '{body_name}'")
    finally:
        backend.disconnect()
```

- [ ] **Step 2: 验证 + Commit**

```bash
cd D:\桌面文件\fc && python -c "from fc_cli.main import cli; print('body remove-feature OK')"
git add packages/cli/src/fc_cli/commands/body.py
git commit -m "feat(body): add body remove-feature command"
```

---

## Part C: 创建 SKILL.md 文件

### Task C1: 创建 fc-part SKILL.md

**Files:**
- Create: `docs/skills/fc-part/SKILL.md`

- [ ] **Step 1: 创建目录和文件**

```bash
mkdir -p "D:\桌面文件\fc\docs\skills\fc-part"
```

- [ ] **Step 2: 写入 SKILL.md**

```markdown
---
name: fc-part
description: FreeCAD Part 工作台命令 — 3D 基元创建、布尔操作、变换、倒角/圆角、孔。用于创建和管理基础 3D 几何体。
---

# fc-part — FreeCAD Part 工作台 CLI 命令

## 命令组概览

| 命令 | 说明 |
|------|------|
| `part add <type>` | 创建 3D 基元（box/cylinder/sphere/cone/torus/wedge/helix/ellipsoid/spiral）|
| `part remove <name>` | 删除对象 |
| `part list` | 列出所有对象 |
| `part get <name>` | 获取对象详情 |
| `part transform <name>` | 变换位置/旋转 |
| `part boolean <op> <base> <tool>` | 布尔操作（cut/fuse/common）|
| `part copy <name>` | 复制对象 |
| `part mirror <name>` | 镜像对象 |
| `part scale <name> <factor>` | 缩放对象 |
| `part fillet-3d <name>` | 3D 圆角 |
| `part chamfer-3d <name>` | 3D 倒角 |
| `part hole <name>` | 打孔 |
| `part info <name>` | 详细信息 |
| `part bounds <name>` | 边界框 |

## 3D 基元参数速查

### box（立方体）
```
fc part add box --name MyBox -P Length=20 -P Width=15 -P Height=10
```

### cylinder（圆柱体）
```
fc part add cylinder --name MyCyl -P Radius=5 -P Height=20
```

### sphere（球体）
```
fc part add sphere --name MySphere -P Radius=10
```

### cone（圆锥体）
```
fc part add cone --name MyCone -P Radius1=10 -P Radius2=0 -P Height=15
```

### torus（圆环体）
```
fc part add torus --name MyTorus -P Radius1=10 -P Radius2=2
```

### wedge（楔形体）
```
fc part add wedge --name MyWedge
```

### helix（螺旋体）
```
fc part add helix --name MyHelix
```

### ellipsoid（椭球体）
```
fc part add ellipsoid --name MyEllipsoid -P Radius1=10 -P Radius2=5 -P Radius3=3
```

## 典型工作流

### 工作流 1：创建带孔的法兰盘
```bash
fc document new --name Flange
fc part add cylinder --name FlangeBody -P Radius=50 -P Height=10
fc part add cylinder --name BoltHole -P Radius=3 -P Height=15
fc part boolean cut FlangeBody BoltHole --name FlangeWithHole
fc export step --output flange.step
```

### 工作流 2：创建 L 型支架
```bash
fc document new --name Bracket
fc part add box --name Vertical -P Length=10 -P Width=50 -P Height=80 --position 0,0,0
fc part add box --name Horizontal -P Length=50 -P Width=50 -P Height=10 --position 0,0,0
fc part boolean fuse Vertical Horizontal --name Bracket
fc part fillet-3d Bracket --radius 2 --edges 12,13
fc export step --output bracket.step
```

## 注意事项

- 所有命令支持 `--json` 输出
- `part add` 的 `--param/-P` 接受 `key=value` 格式，可重复
- `part boolean` 操作后原始对象保留，结果为新对象
- `part fillet-3d` 和 `part chamfer-3d` 的 `--edges` 可以是 `all` 或逗号分隔的索引
- `part scale` 的 factor 可以是单个数字（均匀）或 `x,y,z`（非均匀）
```

- [ ] **Step 3: Commit**

```bash
git add docs/skills/fc-part/SKILL.md
git commit -m "docs(skills): add fc-part SKILL.md"
```

---

### Task C2: 创建 fc-part-design SKILL.md

**Files:**
- Create: `docs/skills/fc-part-design/SKILL.md`

- [ ] **Step 1: 创建目录和文件**

```bash
mkdir -p "D:\桌面文件\fc\docs\skills\fc-part-design"
```

- [ ] **Step 2: 写入 SKILL.md**

```markdown
---
name: fc-part-design
description: FreeCAD PartDesign 工作台命令 — Body 管理、凸台/凹槽、阵列、孔、抽壳、拔模、基准特征。用于参数化 3D 建模。
---

# fc-part-design — FreeCAD PartDesign 工作台 CLI 命令

## 命令组概览

| 命令 | 说明 |
|------|------|
| `body new` | 创建新 Body |
| `body pad <body> <sketch>` | 凸台（拉伸）|
| `body pocket <body> <sketch>` | 凹槽（拉伸切割）|
| `body fillet <body>` | 圆角 |
| `body chamfer <body>` | 倒角 |
| `body revolution <body> <sketch>` | 旋转凸台 |
| `body groove <body> <sketch>` | 旋转凹槽 |
| `body pattern-linear <body> <feature>` | 线性阵列 |
| `body pattern-polar <body> <feature>` | 圆周阵列 |
| `body pattern-mirror <body> <feature>` | 镜像阵列 |
| `body hole <body> <sketch>` | 孔特征 |
| `body shell <body>` | 抽壳 |
| `body draft <body>` | 拔模斜度 |
| `body datum-plane <body>` | 基准面 |
| `body datum-point <body>` | 基准点 |
| `body datum-line <body>` | 基准线 |
| `body set-tip <body>` | 设置建模位置（Tip）|
| `body remove-feature <body> <feature>` | 移除特征 |
| `body list` | 列出所有 Body |
| `body get <name>` | 获取 Body 详情 |

## PartDesign 核心概念

**Body** 是 PartDesign 的核心容器，包含一系列有序的 Feature（特征）。
- **Tip**：Body 中当前"活跃"的特征，新操作在 Tip 之后添加
- **Feature 顺序**：特征按添加顺序执行，顺序影响最终结果
- **基准特征**（Datum）：参考几何，不产生实体但为其他特征提供参考

## 典型工作流

### 工作流 1：参数化零件（法兰盘）
```bash
fc document new --name Flange
fc body new --name FlangeBody
fc sketch new --name FlangeSketch --plane XY
fc sketch add-circle FlangeSketch --center 0,0 --radius 50
fc sketch close FlangeSketch
fc body pad FlangeBody FlangeSketch --length 10
fc sketch new --name HoleSketch --plane XY
fc sketch add-circle HoleSketch --center 35,0 --radius 3
fc sketch close HoleSketch
fc body hole FlangeBody HoleSketch --diameter 6 --depth 10
fc body pattern-polar FlangeBody Hole --count 6 --angle 360
fc export step --output flange.step
```

### 工作流 2：带拔模的壳体零件
```bash
fc document new --name Housing
fc body new --name HousingBody
fc sketch new --name BaseSketch --plane XY
fc sketch add-rect BaseSketch --corner 0,0 --width 100 --height 80
fc sketch close BaseSketch
fc body pad HousingBody BaseSketch --length 50
fc body shell HousingBody --thickness 3 --faces 0
fc body draft HousingBody --angle 3 --faces 1,2,3,4
fc export step --output housing.step
```

### 工作流 3：使用基准面创建偏移特征
```bash
fc document new --name OffsetPart
fc body new --name MainBody
fc sketch new --name BaseSketch --plane XY
fc sketch add-rect BaseSketch --corner 0,0 --width 50 --height 50
fc sketch close BaseSketch
fc body pad MainBody BaseSketch --length 20
fc body datum-plane MainBody --name TopPlane --plane XY --offset 20
fc sketch new --name TopSketch --plane XY --offset 20
fc sketch add-circle TopSketch --center 25,25 --radius 10
fc sketch close TopSketch
fc body pad MainBody TopSketch --length 15
fc export step --output offset_part.step
```

## 注意事项

- 所有命令支持 `--json` 输出
- `body pad/pocket` 的 `--length` 单位为 mm
- `body pattern-linear` 的 `--spacing` 是相邻实例间的距离
- `body pattern-polar` 的 `--angle` 是总角度（360 = 完整圆周）
- `body shell` 的 `--faces` 是要移除的面索引（逗号分隔）
- `body draft` 的 `--angle` 单位为度
- `body set-tip` 不指定 `--feature` 时自动设为最后一个特征
- 基准特征（datum）不产生实体几何，但可作为其他特征的参考
```

- [ ] **Step 3: Commit**

```bash
git add docs/skills/fc-part-design/SKILL.md
git commit -m "docs(skills): add fc-part-design SKILL.md"
```

---

## Part D: 最终验证

### Task D1: 全量验证

- [ ] **Step 1: 验证所有新命令可导入**

```bash
cd D:\桌面文件\fc && python -c "
from fc_cli.main import cli
from click.testing import CliRunner
runner = CliRunner()

# 验证所有新命令存在
new_commands = [
    'part hole',
    'body pattern-linear', 'body pattern-polar', 'body pattern-mirror',
    'body hole', 'body shell', 'body draft',
    'body datum-plane', 'body datum-point', 'body datum-line',
    'body set-tip', 'body remove-feature',
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

- [ ] **Step 2: 运行现有测试确保无回归**

```bash
cd D:\桌面文件\fc && python -m pytest packages/cli/tests/ -v --tb=short
```

Expected: 20 passed（原有测试全部通过）

- [ ] **Step 3: 验证 SKILL.md 文件**

```bash
dir "D:\桌面文件\fc\docs\skills" /b
```

Expected: `fc-part` 和 `fc-part-design` 目录存在，各含 SKILL.md

- [ ] **Step 4: 最终 commit**

```bash
git log --oneline -15
```

确认所有提交记录完整。
