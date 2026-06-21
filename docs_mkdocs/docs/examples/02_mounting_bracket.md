# 示例 2：带凸台和倒角的安装支架

**难度**: 中等
**命令组**: document, sketch, body, part, export
**步骤数**: 12

## 需求

创建一个带凸台和倒角的安装支架：底板 80x60x10，中心凸台直径 30 高 20，凸台中心孔直径 10，底板四个角倒角 C5。

## 阶段1: 工具选型

| 命令组 | 命令 | 用途 |
|--------|------|------|
| document | `document new` | 创建新文档 |
| body | `body new` | 创建 PartDesign Body |
| sketch | `sketch new` | 创建底板草图 |
| sketch | `sketch add-rect` | 绘制底板矩形 |
| sketch | `sketch close` | 关闭草图 |
| body | `body pad` | 拉伸底板 |
| sketch | `sketch new` | 创建凸台草图 |
| sketch | `sketch add-circle` | 绘制凸台圆 |
| sketch | `sketch close` | 关闭草图 |
| body | `body pad` | 拉伸凸台 |
| body | `body hole` | 创建凸台中心孔 |
| part | `part fillet-3d` | 底板四角倒角 |
| export | `export step` | 导出 STEP 文件 |

## 阶段2: 任务拆解

1. 创建新文档 `BracketDoc`
2. 创建 Body `BracketBody`
3. 创建底板草图 `BaseSketch`：80x60 矩形，中心在原点
4. 关闭底板草图
5. 拉伸底板 `BasePad`：长度 10mm
6. 创建凸台草图 `BossSketch`：直径 30 圆，中心在底板顶面中心
7. 关闭凸台草图
8. 拉伸凸台 `BossPad`：长度 20mm
9. 创建凸台中心孔 `CenterHole`：直径 10，深度 20
10. 对底板四角倒角 `ChamferResult`：C5（5mm）
11. 导出 STEP 文件

## 阶段3: 坐标与依赖计算

### 步骤 1：创建文档
- 无依赖
- 文档名: `BracketDoc`

### 步骤 2：创建 Body
- 依赖: 文档已创建
- 名称: `BracketBody`

### 步骤 3：创建底板草图
- 依赖: Body 已创建
- 平面: XY
- 矩形中心: `0, 0`（底板中心在原点）
- 矩形范围: X[-40, 40], Y[-30, 30]
- 命令: `add-rect --corner -40,-30 --width 80 --height 60`

### 步骤 4：关闭底板草图
- 依赖: `BaseSketch` 已创建

### 步骤 5：拉伸底板
- 依赖: `BaseSketch` 已关闭
- 长度: 10mm
- 结果: `BasePad`（Z 方向从 0 到 10）

### 步骤 6：创建凸台草图
- 依赖: `BasePad` 已创建
- 平面: XY，偏移到 Z=10（底板顶面）
- 圆心: `0, 0, 10`（底板中心正上方）
- 半径: 15mm（直径 30）

### 步骤 7：关闭凸台草图
- 依赖: `BossSketch` 已创建

### 步骤 8：拉伸凸台
- 依赖: `BossSketch` 已关闭
- 长度: 20mm（从 Z=10 到 Z=30）
- 结果: `BossPad`

### 步骤 9：创建凸台中心孔
- 依赖: `BossPad` 已创建
- 在凸台顶面创建草图，中心 `0, 0, 30`
- 孔直径: 10，深度: 20
- 结果: `CenterHole`

### 步骤 10：底板四角倒角
- 依赖: `CenterHole` 已创建
- 倒角大小: 5mm（C5）
- 选择底板四角的四条边
- 结果: `BracketWithChamfer`

### 步骤 11：导出 STEP
- 依赖: 所有特征完成
- 输出路径: `mounting_bracket.step`

## 阶段4: 依赖校验

| 步骤 | 依赖 | 状态 |
|------|------|------|
| 1. document new | 无 | 合法 |
| 2. body new | 文档存在 | 合法 |
| 3. sketch new (BaseSketch) | Body 存在 | 合法 |
| 4. sketch close (BaseSketch) | BaseSketch 已创建 | 合法 |
| 5. body pad (BasePad) | BaseSketch 已关闭 | 合法 |
| 6. sketch new (BossSketch) | BasePad 已创建 | 合法 |
| 7. sketch close (BossSketch) | BossSketch 已创建 | 合法 |
| 8. body pad (BossPad) | BossSketch 已关闭 | 合法 |
| 9. body hole (CenterHole) | BossPad 已创建 | 合法 |
| 10. part fillet-3d | CenterHole 已创建 | 合法 |
| 11. export step | 所有特征完成 | 合法 |

所有依赖关系正确，特征顺序符合 PartDesign 建模规则。

## 阶段5: 命令输出

```bash
# 1. 创建新文档
fc document new --name BracketDoc --json

# 2. 创建 PartDesign Body
fc body new --name BracketBody --json

# 3. 创建底板草图（80x60 矩形，中心在原点）
fc sketch new --name BaseSketch --plane XY --json
fc sketch add-rect BaseSketch --corner -40,-30 --width 80 --height 60 --json

# 4. 关闭底板草图
fc sketch close BaseSketch --json

# 5. 拉伸底板（高度 10mm）
fc body pad BracketBody BaseSketch --length 10 --json

# 6. 创建凸台草图（直径 30 圆，在底板顶面 Z=10）
fc sketch new --name BossSketch --plane XY --offset 10 --json
fc sketch add-circle BossSketch --center 0,0 --radius 15 --json

# 7. 关闭凸台草图
fc sketch close BossSketch --json

# 8. 拉伸凸台（高度 20mm）
fc body pad BracketBody BossSketch --length 20 --json

# 9. 创建凸台中心孔（直径 10，深度 20）
fc sketch new --name HoleSketch --plane XY --offset 30 --json
fc sketch add-circle HoleSketch --center 0,0 --radius 5 --json
fc sketch close HoleSketch --json
fc body hole BracketBody HoleSketch --diameter 10 --depth 20 --json

# 10. 底板四角倒角 C5
fc part fillet-3d BracketBody --radius 5 --json

# 11. 导出 STEP 文件
fc export step --output mounting_bracket.step --overwrite --json
```

## 完整命令序列

```bash
fc document new --name BracketDoc --json
fc body new --name BracketBody --json
fc sketch new --name BaseSketch --plane XY --json
fc sketch add-rect BaseSketch --corner -40,-30 --width 80 --height 60 --json
fc sketch close BaseSketch --json
fc body pad BracketBody BaseSketch --length 10 --json
fc sketch new --name BossSketch --plane XY --offset 10 --json
fc sketch add-circle BossSketch --center 0,0 --radius 15 --json
fc sketch close BossSketch --json
fc body pad BracketBody BossSketch --length 20 --json
fc sketch new --name HoleSketch --plane XY --offset 30 --json
fc sketch add-circle HoleSketch --center 0,0 --radius 5 --json
fc sketch close HoleSketch --json
fc body hole BracketBody HoleSketch --diameter 10 --depth 20 --json
fc part fillet-3d BracketBody --radius 5 --json
fc export step --output mounting_bracket.step --overwrite --json
```

## 预期输出

```json
// 1. document new
{"status": "ok", "operation": "document_new", "data": {"name": "BracketDoc"}, "message": "Document 'BracketDoc' created"}

// 2. body new
{"status": "ok", "operation": "body_new", "data": {"name": "BracketBody"}, "message": "Body 'BracketBody' created"}

// 3. sketch new + add-rect
{"status": "ok", "operation": "sketch_new", "data": {"name": "BaseSketch"}, "message": "Sketch 'BaseSketch' created on XY plane"}
{"status": "ok", "operation": "sketch_add_rect", "data": {"indices": [0, 1, 2, 3]}, "message": "Rectangle added to 'BaseSketch'"}

// 4. sketch close
{"status": "ok", "operation": "sketch_close", "data": {"status": "closed"}, "message": "Sketch 'BaseSketch' closed"}

// 5. body pad
{"status": "ok", "operation": "body_pad", "data": {"feature": "Pad"}, "message": "Pad created: length=10"}

// 6-7. BossSketch
{"status": "ok", "operation": "sketch_new", "data": {"name": "BossSketch"}, "message": "Sketch 'BossSketch' created on XY plane at offset 10"}
{"status": "ok", "operation": "sketch_add_circle", "data": {"index": 0}, "message": "Circle added to 'BossSketch'"}
{"status": "ok", "operation": "sketch_close", "data": {"status": "closed"}, "message": "Sketch 'BossSketch' closed"}

// 8. body pad (Boss)
{"status": "ok", "operation": "body_pad", "data": {"feature": "Pad001"}, "message": "Pad created: length=20"}

// 9. hole
{"status": "ok", "operation": "sketch_new", "data": {"name": "HoleSketch"}, "message": "Sketch 'HoleSketch' created"}
{"status": "ok", "operation": "sketch_add_circle", "data": {"index": 0}, "message": "Circle added"}
{"status": "ok", "operation": "sketch_close", "data": {"status": "closed"}, "message": "Sketch closed"}
{"status": "ok", "operation": "body_hole", "data": {"feature": "Hole"}, "message": "Hole created: diameter=10, depth=20"}

// 10. fillet
{"status": "ok", "operation": "part_fillet_3d", "data": {"result": "Fillet"}, "message": "Fillet created: radius=5"}

// 11. export
{"status": "ok", "operation": "export_step", "data": {"file": "mounting_bracket.step", "size": 28456}, "message": "Exported to mounting_bracket.step"}
```
