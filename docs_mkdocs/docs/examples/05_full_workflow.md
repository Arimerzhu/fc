# 示例 5：从需求到工程图完整工作流

**难度**: 复杂
**命令组**: document, sketch, body, part, techdraw, export
**步骤数**: 24

## 需求

从需求到工程图：创建一个 60x40x20 的带盖盒子，壁厚 2mm，底部有 4 个直径 6 的安装孔，生成三视图工程图并导出 PDF。

## 阶段1: 工具选型

| 命令组 | 命令 | 用途 |
|--------|------|------|
| document | `document new` | 创建新文档 |
| body | `body new` | 创建 Body |
| sketch | `sketch new` | 创建草图 |
| sketch | `sketch add-rect` | 绘制外轮廓 |
| sketch | `sketch close` | 关闭草图 |
| body | `body pad` | 拉伸主体 |
| body | `body shell` | 抽壳 |
| sketch | `sketch new` | 创建安装孔草图 |
| sketch | `sketch add-circle` | 绘制安装孔 |
| sketch | `sketch close` | 关闭草图 |
| body | `body hole` | 创建安装孔 |
| body | `body pattern-linear` | 阵列安装孔 |
| part | `part fillet-3d` | 边缘圆角 |
| techdraw | `techdraw page` | 创建工程图页面 |
| techdraw | `techdraw view` | 添加三视图 |
| techdraw | `techdraw dimension` | 添加标注 |
| techdraw | `techdraw annotation` | 添加注释 |
| export | `export pdf` | 导出 PDF |

## 阶段2: 任务拆解

**Part A: 三维建模**

1. 创建新文档 `BoxDoc`
2. 创建 Body `BoxBody`
3. 创建底面草图 `BaseSketch`：60x40 矩形
4. 关闭草图
5. 拉伸主体 `MainPad`：高度 20mm
6. 抽壳 `ShellBody`：壁厚 2mm，移除顶面
7. 创建安装孔草图 `HoleSketch`：在底板内底面绘制 4 个孔
8. 关闭草图
9. 创建孔特征 `MountingHole`：直径 6
10. 线性阵列孔 `HolePattern`：2x2 阵列
11. 边缘圆角 `FilletResult`：R1

**Part B: 工程图**

12. 创建 A3 工程图页面 `DrawingPage`
13. 添加俯视图 `TopView`：方向 0,0,1
14. 添加前视图 `FrontView`：方向 0,1,0
15. 添加侧视图 `SideView`：方向 1,0,0
16. 添加长度标注（俯视图）
17. 添加宽度标注（俯视图）
18. 添加高度标注（前视图）
19. 添加标题注释
20. 导出 PDF

## 阶段3: 坐标与依赖计算

### 主体几何

- 底面矩形中心: `0, 0`
- 底面矩形范围: X[-30, 30], Y[-20, 20]
- 拉伸高度: 20mm（Z=0 到 Z=20）
- 抽壳厚度: 2mm
- 内腔尺寸: 长=56, 宽=36, 高=18

### 安装孔几何

- 孔径: 6mm（半径 3mm）
- 孔中心距边缘: 8mm
- 孔位置（内底面 Z=2 处）:

| 孔 | X | Y |
|----|---|---|
| 1 | -22 | -12 |
| 2 | -22 | 12 |
| 3 | 22 | -12 |
| 4 | 22 | 12 |

- 阵列参数：X 方向 2 个间距 44mm，Y 方向 2 个间距 24mm

### 工程图布局

- 页面: A3 (420x297mm)
- 俯视图: 页面左上，比例 1:2
- 前视图: 页面左下，比例 1:2
- 侧视图: 页面右侧，比例 1:2

### 步骤依赖

| 步骤 | 操作 | 依赖 | 输出 |
|------|------|------|------|
| 1 | document new | 无 | `BoxDoc` |
| 2 | body new | 文档 | `BoxBody` |
| 3 | sketch new (BaseSketch) | Body | `BaseSketch` |
| 4 | sketch add-rect | `BaseSketch` | 矩形 |
| 5 | sketch close | `BaseSketch` | 关闭 |
| 6 | body pad | 草图 | `MainPad` |
| 7 | body shell | `MainPad` | `ShellBody` |
| 8 | sketch new (HoleSketch) | `ShellBody` | `HoleSketch` |
| 9 | sketch add-circle x4 | `HoleSketch` | 4 个圆 |
| 10 | sketch close | `HoleSketch` | 关闭 |
| 11 | body hole | 草图 | `MountingHole` |
| 12 | body pattern-linear | `MountingHole` | `HolePattern` |
| 13 | part fillet-3d | `HolePattern` | `FilletResult` |
| 14 | techdraw page | 模型 | `DrawingPage` |
| 15 | techdraw view x3 | `DrawingPage`, 模型 | 三视图 |
| 16 | techdraw dimension x3 | 视图 | 标注 |
| 17 | techdraw annotation | `DrawingPage` | 注释 |
| 18 | export pdf | 页面 | PDF |

## 阶段4: 依赖校验

**建模阶段**：
- Body -> Sketch -> Pad -> Shell -> Hole -> Pattern -> Fillet
- 严格顺序依赖，符合 PartDesign 特征树规则

**工程图阶段**：
- 模型完成后才能创建页面
- 页面存在后才能添加视图
- 视图存在后才能添加标注
- 所有依赖关系正确

## 阶段5: 命令输出

```bash
# ============================================================
# Part A: 三维建模
# ============================================================

# 1. 创建新文档
fc document new --name BoxDoc --json

# 2. 创建 Body
fc body new --name BoxBody --json

# 3. 创建底面草图（60x40 矩形，中心在原点）
fc sketch new --name BaseSketch --plane XY --json
fc sketch add-rect BaseSketch --corner -30,-20 --width 60 --height 40 --json

# 4. 关闭草图
fc sketch close BaseSketch --json

# 5. 拉伸主体（高度 20mm）
fc body pad BoxBody BaseSketch --length 20 --json

# 6. 抽壳（壁厚 2mm，移除顶面形成开口盒子）
fc body shell BoxBody --thickness 2 --faces 0 --json

# 7. 创建安装孔草图（在内底面 Z=2 处）
fc sketch new --name HoleSketch --plane XY --offset 2 --json

# 8. 绘制 4 个安装孔（直径 6，距边缘 8mm）
fc sketch add-circle HoleSketch --center -22,-12 --radius 3 --json
fc sketch add-circle HoleSketch --center -22,12 --radius 3 --json
fc sketch add-circle HoleSketch --center 22,-12 --radius 3 --json
fc sketch add-circle HoleSketch --center 22,12 --radius 3 --json

# 9. 关闭安装孔草图
fc sketch close HoleSketch --json

# 10. 创建孔特征（直径 6，深度 2mm 穿透底板）
fc body hole BoxBody HoleSketch --diameter 6 --depth 2 --json

# 11. 边缘圆角 R1（美化盒子边缘）
fc part fillet-3d BoxBody --radius 1 --json

# ============================================================
# Part B: 工程图
# ============================================================

# 12. 创建 A3 工程图页面
fc techdraw page --name DrawingPage --format A3 --json

# 13. 添加俯视图（从 +Z 方向看）
fc techdraw view --page DrawingPage --source BoxBody --name TopView --direction 0,0,1 --scale 0.5 --json

# 14. 添加前视图（从 +Y 方向看）
fc techdraw view --page DrawingPage --source BoxBody --name FrontView --direction 0,1,0 --scale 0.5 --json

# 15. 添加侧视图（从 +X 方向看）
fc techdraw view --page DrawingPage --source BoxBody --name SideView --direction 1,0,0 --scale 0.5 --json

# 16. 添加长度标注（俯视图，60mm）
fc techdraw dimension --view TopView --type distance --elements 0,1 --json

# 17. 添加宽度标注（俯视图，40mm）
fc techdraw dimension --view TopView --type distance --elements 1,2 --json

# 18. 添加高度标注（前视图，20mm）
fc techdraw dimension --view FrontView --type distance --elements 0,1 --json

# 19. 添加标题注释
fc techdraw annotation --page DrawingPage --text "Box Assembly - 60x40x20" --position 10,270 --json

# 20. 导出 PDF 工程图
fc techdraw export DrawingPage --output box_drawing.pdf --format pdf --json

# 21. 同时导出 STEP 三维模型
fc export step --output box_model.step --overwrite --json

# 22. 保存项目文件
fc document save --output box_project.FCStd --json
```

## 完整命令序列

```bash
# === 三维建模 ===
fc document new --name BoxDoc --json
fc body new --name BoxBody --json
fc sketch new --name BaseSketch --plane XY --json
fc sketch add-rect BaseSketch --corner -30,-20 --width 60 --height 40 --json
fc sketch close BaseSketch --json
fc body pad BoxBody BaseSketch --length 20 --json
fc body shell BoxBody --thickness 2 --faces 0 --json
fc sketch new --name HoleSketch --plane XY --offset 2 --json
fc sketch add-circle HoleSketch --center -22,-12 --radius 3 --json
fc sketch add-circle HoleSketch --center -22,12 --radius 3 --json
fc sketch add-circle HoleSketch --center 22,-12 --radius 3 --json
fc sketch add-circle HoleSketch --center 22,12 --radius 3 --json
fc sketch close HoleSketch --json
fc body hole BoxBody HoleSketch --diameter 6 --depth 2 --json
fc part fillet-3d BoxBody --radius 1 --json

# === 工程图 ===
fc techdraw page --name DrawingPage --format A3 --json
fc techdraw view --page DrawingPage --source BoxBody --name TopView --direction 0,0,1 --scale 0.5 --json
fc techdraw view --page DrawingPage --source BoxBody --name FrontView --direction 0,1,0 --scale 0.5 --json
fc techdraw view --page DrawingPage --source BoxBody --name SideView --direction 1,0,0 --scale 0.5 --json
fc techdraw dimension --view TopView --type distance --elements 0,1 --json
fc techdraw dimension --view TopView --type distance --elements 1,2 --json
fc techdraw dimension --view FrontView --type distance --elements 0,1 --json
fc techdraw annotation --page DrawingPage --text "Box Assembly - 60x40x20" --position 10,270 --json
fc techdraw export DrawingPage --output box_drawing.pdf --format pdf --json
fc export step --output box_model.step --overwrite --json
fc document save --output box_project.FCStd --json
```

## 预期输出

```json
// === 三维建模 ===
// 1. document new
{"status": "ok", "operation": "document_new", "data": {"name": "BoxDoc"}, "message": "Document 'BoxDoc' created"}

// 2. body new
{"status": "ok", "operation": "body_new", "data": {"name": "BoxBody"}, "message": "Body 'BoxBody' created"}

// 3-5. sketch + close
{"status": "ok", "operation": "sketch_new", "data": {"name": "BaseSketch"}, "message": "Sketch 'BaseSketch' created on XY plane"}
{"status": "ok", "operation": "sketch_add_rect", "data": {"indices": [0, 1, 2, 3]}, "message": "Rectangle added to 'BaseSketch'"}
{"status": "ok", "operation": "sketch_close", "data": {"status": "closed"}, "message": "Sketch 'BaseSketch' closed"}

// 6. body pad
{"status": "ok", "operation": "body_pad", "data": {"feature": "Pad"}, "message": "Pad created: length=20"}

// 7. body shell
{"status": "ok", "operation": "body_shell", "data": {"feature": "Shell"}, "message": "Shell created: thickness=2, removed faces: [0]"}

// 8-10. hole sketch + close
{"status": "ok", "operation": "sketch_new", "data": {"name": "HoleSketch"}, "message": "Sketch 'HoleSketch' created on XY plane at offset 2"}
{"status": "ok", "operation": "sketch_add_circle", "data": {"index": 0}, "message": "Circle added"}
{"status": "ok", "operation": "sketch_add_circle", "data": {"index": 1}, "message": "Circle added"}
{"status": "ok", "operation": "sketch_add_circle", "data": {"index": 2}, "message": "Circle added"}
{"status": "ok", "operation": "sketch_add_circle", "data": {"index": 3}, "message": "Circle added"}
{"status": "ok", "operation": "sketch_close", "data": {"status": "closed"}, "message": "Sketch 'HoleSketch' closed"}

// 11. body hole
{"status": "ok", "operation": "body_hole", "data": {"feature": "Hole"}, "message": "Hole created: diameter=6, depth=2"}

// 12. fillet
{"status": "ok", "operation": "part_fillet_3d", "data": {"result": "Fillet"}, "message": "Fillet created: radius=1"}

// === 工程图 ===
// 13. techdraw page
{"status": "ok", "operation": "techdraw_page", "data": {"name": "DrawingPage", "format": "A3"}, "message": "Page 'DrawingPage' created (A3)"}

// 14-16. techdraw view x3
{"status": "ok", "operation": "techdraw_view", "data": {"name": "TopView"}, "message": "View 'TopView' added to page"}
{"status": "ok", "operation": "techdraw_view", "data": {"name": "FrontView"}, "message": "View 'FrontView' added to page"}
{"status": "ok", "operation": "techdraw_view", "data": {"name": "SideView"}, "message": "View 'SideView' added to page"}

// 17-19. techdraw dimension x3
{"status": "ok", "operation": "techdraw_dimension", "data": {"type": "distance"}, "message": "Dimension added to TopView"}
{"status": "ok", "operation": "techdraw_dimension", "data": {"type": "distance"}, "message": "Dimension added to TopView"}
{"status": "ok", "operation": "techdraw_dimension", "data": {"type": "distance"}, "message": "Dimension added to FrontView"}

// 20. techdraw annotation
{"status": "ok", "operation": "techdraw_annotation", "data": {"name": "Annotation001"}, "message": "Annotation added to page"}

// 21. techdraw export
{"status": "ok", "operation": "techdraw_export", "data": {"file": "box_drawing.pdf"}, "message": "Exported to box_drawing.pdf"}

// 22. export step
{"status": "ok", "operation": "export_step", "data": {"file": "box_model.step", "size": 32145}, "message": "Exported to box_model.step"}

// 23. document save
{"status": "ok", "operation": "document_save", "data": {"path": "box_project.FCStd"}, "message": "Saved to box_project.FCStd"}
```

## 工作流总结

本示例展示了从需求到工程图的完整工作流：

```
需求定义 -> 三维建模 -> 工程图生成 -> 文档交付
    |           |            |            |
    v           v            v            v
 参数计算    特征树构建    视图创建      PDF 导出
             草图+拉伸    尺寸标注      STEP 导出
             抽壳+打孔    注释说明      FCStd 保存
```

**关键要点**：
1. 建模阶段严格遵循 PartDesign 特征顺序
2. 工程图阶段依赖已完成的三维模型
3. 所有命令使用 `--json` 格式输出，便于 AI Agent 解析
4. 使用 `--project` 参数可在多步骤间保持会话状态
