---
name: fc-part-design
description: FreeCAD PartDesign 工作台命令 — Body 管理、凸台/凹槽、阵列、孔、抽壳、拔模、基准特征。用于参数化 3D 建模。
---

# fc-part-design — FreeCAD PartDesign 工作台 CLI 命令

## 命令组概览（20 个命令）

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

### 工作流 4：线性阵列 + 镜像
```bash
fc document new --name Bracket
fc body new --name BracketBody
fc sketch new --name BaseSketch --plane XY
fc sketch add-rect BaseSketch --corner 0,0 --width 60 --height 40
fc sketch close BaseSketch
fc body pad BracketBody BaseSketch --length 10
fc sketch new --name SlotSketch --plane XY
fc sketch add-rect SlotSketch --corner 5,15 --width 10 --height 10
fc sketch close SlotSketch
fc body pocket BracketBody SlotSketch --length 10
fc body pattern-linear BracketBody Pocket --direction X --count 4 --spacing 12
fc export step --output bracket.step
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
- `body remove-feature` 从 Body 中移除特征，后续特征可能受影响
