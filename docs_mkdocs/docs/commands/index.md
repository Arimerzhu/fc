# 命令参考

fc 共有 **17 个命令组**，**185+ 个命令**，覆盖所有 FreeCAD 工作台。

## 命令组一览

| 命令组 | 命令数 | 说明 |
|--------|--------|------|
| [Document](document.md) | 6 | 文档生命周期（新建/打开/保存/关闭/列表/信息） |
| [Part](part.md) | 14 | 零件基元与操作（box/cylinder/sphere/boolean/fillet/chamfer 等） |
| [Sketch](sketch.md) | 21 | 2D 草图（直线/圆/矩形/圆弧/约束） |
| [Body](body.md) | 20 | PartDesign 特征（pad/pocket/revolution/fillet/pattern 等） |
| [Export](export.md) | 14 | 文件导出（STEP/STL/OBJ/BREP/DXF/SVG/PDF/glTF/3MF/FCStd） |
| [Import](import.md) | 11 | 文件导入（自动检测/STEP/STL/OBJ/DXF/BREP） |
| [Session](session.md) | 6 | 会话管理（undo/redo/status/history/snapshot/restore） |
| [Execute](execute.md) | 2 | 原始 Python 执行（code/file） |
| [Mesh](mesh.md) | 14 | 网格操作（导入/导出/分析/修复/细化/简化/布尔） |
| [Draft](draft.md) | 15 | Draft 工作台（线/多段线/圆/弧/矩形/文字/尺寸/阵列） |
| [Surface](surface.md) | 9 | 曲面操作（loft/sweep/fill/pipe/offset/thicken/flatten/sew） |
| [TechDraw](techdraw.md) | 8 | 工程图（页面/视图/尺寸/注释/符号/导出） |
| [Spreadsheet](spreadsheet.md) | 11 | 电子表格驱动设计（创建/设置/公式/别名/链接） |
| [Material](material.md) | 9 | 材料管理（列表/显示/分配/创建/编辑/导出/导入） |
| [Assembly](assembly.md) | 10 | 装配操作（创建/添加/约束/求解/爆炸/动画） |
| [FEM](fem.md) | 8 | 有限元分析（分析/网格/材料/约束/求解/结果） |
| [CAM](cam.md) | 7 | CAM 操作（job/刀具/刀路/后处理/仿真） |

## 全局选项

所有命令支持以下全局选项：

| 选项 | 说明 |
|------|------|
| `--json` | JSON 格式输出（AI Agent 推荐） |
| `--backend headless\|rpc` | 后端选择（headless=FreeCADCmd, rpc=FreeCAD GUI） |
| `--freecad-path PATH` | FreeCAD 可执行文件路径 |
| `--project PATH` | 项目文件路径（会话持久化） |
| `--host HOST` | RPC 主机（默认 localhost） |
| `--port PORT` | RPC 端口（默认 9875） |

## 使用 --json

所有命令推荐使用 `--json` 输出，便于 AI Agent 和脚本消费：

```bash
# 成功响应
fc part add box --name Box --param Length=10 --json
# 输出: {"status": "ok", "operation": "part_add", "data": {"name": "Box", "type": "Part::Box"}, ...}

# 错误响应
fc part get NonExistent --json
# 输出: {"status": "error", "error": {"code": "NOT_FOUND", "message": "...", "suggestion": "..."}}
 ```
