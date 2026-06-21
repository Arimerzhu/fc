---
name: fc-examples
description: fc 示例库 — 5个从简单到复杂的完整示例索引。学习风格时加载。
---

# fc-examples — 示例库索引与模式参考

## 示例索引

| # | 示例 | 难度 | 步骤 | 描述 | 关键命令 |
|---|------|------|------|------|----------|
| 1 | 简单底板通孔 | 简单 | 7 | 100x100x10 底板 + 中心通孔 | `document`, `part`, `export` |
| 2 | 带凸台倒角安装支架 | 中等 | 12 | 底板+凸台+中心孔+C5 倒角 | `document`, `sketch`, `body`, `part`, `export` |
| 3 | 简单装配体 | 中等 | 14 | 底座板 + 4 个圆柱支柱装配 | `document`, `part`, `assembly`, `export` |
| 4 | 参数化盒子设计 | 中等 | 12 | 参数驱动的可调整尺寸盒子 | `document`, `spreadsheet`, `sketch`, `body`, `export` |
| 5 | 需求到工程图完整工作流 | 复杂 | 24 | 带盖盒子建模 + 三视图工程图 + PDF | `document`, `sketch`, `body`, `part`, `techdraw`, `export` |

## 模式库（Pattern Library）

### 模式 1：底板带孔
```bash
fc document new --name Doc --json
fc part add box --name Plate --position 0,0,5 -P Length=100 -P Width=100 -P Height=10 --json
fc part add cylinder --name Hole --position 0,0,5 -P Radius=10 -P Height=15 --json
fc part boolean cut Plate Hole --name Result --json
fc export step --output plate.step --overwrite --json
```

### 模式 2：法兰盘螺栓孔
```bash
fc body new --name Body --json
fc sketch new --name Sketch --plane XY --json
fc sketch add-circle Sketch --center 0,0 --radius 25 --json
fc sketch close Sketch --json
fc body pad Body Sketch --length 10 --json
# 螺栓孔：在凸台草图上打孔后阵列
fc sketch new --name HoleSketch --plane XY --offset 10 --json
fc sketch add-circle HoleSketch --center 20,0 --radius 3 --json
fc sketch close HoleSketch --json
fc body hole Body HoleSketch --diameter 6 --depth 10 --json
```

### 模式 3：L 型支架倒角
```bash
fc part add box --name Vertical --position -5,0,25 -P Length=10 -P Width=50 -P Height=50 --json
fc part add box --name Horizontal --position 25,0,5 -P Length=50 -P Width=50 -P Height=10 --json
fc part boolean fuse Vertical Horizontal --name LBracket --json
fc part fillet-3d LBracket --radius 3 --json
```

### 模式 4：参数化设计（电子表格驱动）
```bash
fc spreadsheet create --name Params --json
fc spreadsheet set --sheet Params --cell A1 --value 100 --json
fc spreadsheet alias --sheet Params --cell A1 --alias Length --json
# 后续草图尺寸引用 Params.Length 实现参数驱动
```

### 模式 5：装配约束
```bash
fc assembly create --name Assy --json
fc assembly add --assembly Assy --object Part1 --json
fc assembly add --assembly Assy --object Part2 --json
fc assembly ground --assembly Assy --object Part1 --json
fc assembly constraint --type coincident --obj1 Part1 --obj2 Part2 --json
fc assembly solve --assembly Assy --json
```

### 模式 6：FEM 分析管道
```bash
fem analysis --name StaticAnalysis --json
fem mesh --analysis StaticAnalysis --object Beam --max-size 5 --json
fem material --analysis StaticAnalysis --material Steel --object Beam --json
fem constraint --analysis StaticAnalysis --type fixed --object Beam --json
fem solve --analysis StaticAnalysis --solver calculix --json
fem result --analysis StaticAnalysis --json
```

### 模式 7：技术工程图管道
```bash
fc techdraw page --name Page --format A3 --json
fc techdraw view --page Page --source Body --name TopView --direction 0,0,1 --scale 0.5 --json
fc techdraw view --page Page --source Body --name FrontView --direction 0,1,0 --scale 0.5 --json
fc techdraw dimension --view TopView --type distance --elements 0,1 --json
fc techdraw annotation --page Page --text "Title" --position 10,270 --json
fc techdraw export --page Page --output drawing.pdf --format pdf --json
```

## 命令使用频率

| 排名 | 命令 | 频率 | 说明 |
|------|------|------|------|
| 1 | `document new` | 每个任务 | 创建文档 |
| 2 | `export step` | 高频 | CAD 交付 |
| 3 | `part add box/cylinder` | 高频 | 基础几何体 |
| 4 | `part boolean cut/fuse` | 高频 | 布尔操作 |
| 5 | `sketch new` | 高频 | 创建草图 |
| 6 | `body pad` | 高频 | 拉伸特征 |
| 7 | `export stl` | 中频 | 3D 打印 |
| 8 | `part fillet-3d` | 中频 | 圆角 |
| 9 | `mesh repair` | 中频 | 网格修复 |
| 10 | `techdraw page/view` | 中频 | 工程图 |

## 快速查找（Quick Lookup）

| 我想... | 加载技能文件 |
|---------|-------------|
| 导出/导入文件 | `DATA_EXCHANGE.md`（本文件同组） |
| 创建基础几何体 | `fc-part/SKILL.md` |
| 绘制 2D 草图 | `fc-sketch/SKILL.md` |
| PartDesign 建模 | `fc-part-design/SKILL.md` |
| 曲面建模 | `fc-surface/SKILL.md` |
| 装配设计 | `fc-assembly/SKILL.md` |
| 有限元分析 | `fc-fem/SKILL.md` |
| 工程图出图 | `fc-techdraw/SKILL.md` |
| 网格处理 | `DATA_EXCHANGE.md`（mesh 部分） |
| 参数化设计 | 示例 4（参数化盒子） |
| 完整工作流参考 | 示例 5（需求到工程图） |
