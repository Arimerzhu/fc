---
name: fc-gui-injection
description: "为 FreeCAD headless 模式生成的 FCStd 文件手动注入 GuiDocument.xml，包含颜色、可见性、透明度、分组等 ViewProvider 数据。Invoke when FCStd files lack GUI data, ViewObject is None in freecadcmd, or user needs color/visibility/transparency in FreeCAD GUI."
---

# fc-gui-injection — FCStd GUI 数据注入

本 Skill 解决 `freecadcmd`（headless 模式）生成的 `.FCStd` 文件在 FreeCAD GUI 中打开时没有颜色、显示模式、透明度等视觉属性的问题。

## 问题根源

- `freecadcmd.exe` 是 FreeCAD 的无界面模式
- 在此模式下 `obj.ViewObject` 为 `None`
- 因此不会生成 `GuiDocument.xml`
- FCStd 打开后所有零件显示为默认灰色

## 配套脚本

脚本位于 `fc/scripts/`：

- **GUI 注入脚本**：`fc/scripts/inject_gui.py`
- **验证脚本**：`fc/scripts/verify_gui.py`

## 使用方法

### 1. 直接为单个 FCStd 注入 GUI

编辑 `fc/scripts/inject_gui.py` 中的配置：

```python
SRC_FCSTD = r"D:\Temp\PaperFeeder.FCStd"      # 源文件（headless 生成）
DST_FCSTD = r"d:\桌面文件\PaperFeeder.FCStd"  # 输出文件
```

修改 `OBJECTS` 列表配置每个对象：

```python
OBJECTS = [
    ("BaseFrame",      "frame",   True,  0),
    ("Cam",            "cam",     True,  20),   # 可见，透明度 20%
    ("Bearing_L",      "tool",    False, 0),    # 隐藏
    # ...
]
```

格式：`(对象名, 颜色键, 可见性, 透明度)`

运行：

```powershell
python "d:\桌面文件\fc\scripts\inject_gui.py"
```

### 2. 验证注入结果

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" "d:\桌面文件\fc\scripts\verify_gui.py"
```

会检查：
- ZIP 完整性
- FreeCAD 能否加载
- GuiDocument.xml 中 ViewProvider 数量
- 是否包含 ShapeColor / Transparency / Visibility / DisplayMode

## 颜色配置

在 `inject_gui.py` 中修改 `COLORS` 字典：

```python
COLORS = {
    "frame":   (191, 191, 191),  # 灰色
    "shaft":   (51, 102, 204),   # 蓝色
    "cam":     (204, 51, 51),    # 红色
    "arm":     (51, 178, 76),    # 绿色
    "tapper":  (204, 128, 51),   # 橙色
    "paper":   (245, 235, 220),  # 米白
    "tool":    (128, 128, 128),  # 深灰（隐藏工具）
}
```

颜色值使用 RGB 0-255。

## GuiDocument.xml 结构

注入的 `GuiDocument.xml` 包含：

- **Camera**：默认等轴测视角
- **ViewProviderData**：每个对象一个 `ViewProvider` 节点
  - `Visibility`：可见/隐藏
  - `DisplayMode`：Shaded / Wireframe
  - `ShapeColor`：面颜色
  - `Transparency`：透明度 0-100
  - `LineWidth`：线宽

## 批量注入思路

如需批量处理多个 FCStd，可扩展 `inject_gui.py`：

1. 读取 FCStd 中的 `Document.xml`，自动提取所有对象名
2. 根据对象名关键词自动分类颜色（参考 `fc-solidworks` 的颜色规则）
3. 生成对应的 `GuiDocument.xml`
4. 重新打包到 FCStd

## 注意事项

1. **备份原文件**：注入前建议备份原始 FCStd
2. **对象名必须匹配**：`GuiDocument.xml` 中的 `ViewProvider name` 必须与 `Document.xml` 中的对象名完全一致
3. **headless 验证**：注入后可用 `freecadcmd.exe` 加载验证，无需启动 GUI
4. **分组信息**：`GuiDocument.xml` 不直接存储分组，分组是 `Document.xml` 中的 `App::DocumentObjectGroup`

## 替代方案

如果可以直接使用 FreeCAD GUI：

```python
import FreeCADGui
FreeCADGui.showMainWindow()
doc = FreeCAD.openDocument("model.FCStd")
for obj in doc.Objects:
    if hasattr(obj, "ViewObject") and obj.ViewObject:
        obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)
doc.save()
```

但在服务器/自动化环境中通常无法启动 GUI，因此需要手动注入 `GuiDocument.xml`。
