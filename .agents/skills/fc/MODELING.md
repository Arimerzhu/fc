---
name: fc-modeling
description: fc 建模技能 — part/sketch/body 命令组。创建几何体时加载。
---

# fc-modeling — 核心 3D 建模命令组

涵盖 `part`（14 命令）、`sketch`（21 命令）、`body`（20 命令）三组，共 55 个命令。

---

## 1. part 命令组（14 个）

> 3D 基元创建、布尔操作、变换、倒角/圆角、孔。

| 命令 | 说明 |
|------|------|
| `part add <type>` | 创建 3D 基元（box/cylinder/sphere/cone/torus/wedge/helix/ellipsoid/spiral）|
| `part remove/list/get <name>` | 删除/列出/获取对象 |
| `part transform <name>` | 变换位置/旋转 |
| `part boolean <op> <base> <tool>` | 布尔操作（cut/fuse/common）|
| `part copy/mirror/scale <name>` | 复制/镜像/缩放 |
| `part fillet-3d/chamfer-3d <name>` | 3D 圆角/倒角 |
| `part hole <name>` | 打孔 |
| `part info/bounds <name>` | 详细信息/边界框 |

### 3D 基元参数速查

```
fc part add box       -P Length=20 -P Width=15 -P Height=10
fc part add cylinder  -P Radius=5  -P Height=20
fc part add sphere    -P Radius=10
fc part add cone      -P Radius1=10 -P Radius2=0 -P Height=15
fc part add torus     -P Radius1=10 -P Radius2=2
fc part add ellipsoid -P Radius1=10 -P Radius2=5 -P Radius3=3
fc part add wedge/helix/spiral
```

### 典型工作流

**法兰盘带孔：**
```bash
fc part add cylinder --name FlangeBody -P Radius=50 -P Height=10
fc part add cylinder --name BoltHole   -P Radius=3  -P Height=15
fc part boolean cut FlangeBody BoltHole --name FlangeWithHole
```

**L 型支架：**
```bash
fc part add box --name Vertical    -P Length=10 -P Width=50 -P Height=80 --position 0,0,0
fc part add box --name Horizontal  -P Length=50 -P Width=50 -P Height=10 --position 0,0,0
fc part boolean fuse Vertical Horizontal --name Bracket
fc part fillet-3d Bracket --radius 2 --edges 12,13
```

**part hole 打孔：**
```bash
fc part add box --name BasePlate -P Length=100 -P Width=80 -P Height=10
fc part hole BasePlate --diameter 8 --depth 10 --position 25,25,0
```

### 关键注意事项
- `--param/-P` 接受 `key=value` 格式，可重复
- `part boolean` 操作后原始对象保留，结果为新对象
- `--edges` 可以是 `all` 或逗号分隔的索引
- `part scale` 的 factor 可以是单个数字（均匀）或 `x,y,z`（非均匀）

---

## 2. sketch 命令组（21 个）

> 2D 草图：几何创建、约束、修剪/镜像/克隆/导出。

| 命令 | 说明 |
|------|------|
| `sketch new` | 创建新草图 |
| `sketch add-line/circle/rect/arc` | 添加线段/圆/矩形/圆弧 |
| `sketch add-ellipse/polygon/bspline/slot/point` | 添加椭圆/多边形/B样条/槽/点 |
| `sketch constrain` | 添加约束 |
| `sketch close/delete-geom/trim` | 关闭/删除/修剪 |
| `sketch mirror/clone` | 镜像/克隆几何 |
| `sketch list/get/validate/solve-status` | 列出/获取/验证/求解状态 |
| `sketch export` | 导出为 DXF |

### 约束类型速查

| 约束 | 说明 | 约束 | 说明 |
|------|------|------|------|
| `horizontal` / `vertical` | 水平 / 垂直 | `distance` / `angle` | 距离 / 角度 |
| `coincident` | 重合 | `radius` / `diameter` | 半径 / 直径 |
| `parallel` / `perpendicular` | 平行 / 垂直 | `tangent` / `symmetric` | 相切 / 对称 |
| `equal` / `fixed` | 等长 / 固定 | `point_on_object` | 点在对象上 |
| `distance_x` / `distance_y` | X / Y 方向距离 | | |

### 典型工作流

**参数化草图：**
```bash
fc sketch new --name MySketch --plane XY
fc sketch add-circle MySketch --center 0,0 --radius 25
fc sketch add-circle MySketch --center 35,0 --radius 5
fc sketch constrain MySketch coincident --elements 0
fc sketch constrain MySketch distance --elements 0,1 --value 35
fc sketch validate MySketch
```

**多边形 + 镜像：**
```bash
fc sketch new --name PolySketch --plane XY
fc sketch add-polygon PolySketch --center 0,0 --radius 20 --sides 6
fc sketch mirror PolySketch --elements 0,1,2 --axis x
fc sketch close PolySketch
```

**B 样条曲线：**
```bash
fc sketch new --name SplineSketch --plane XY
fc sketch add-bspline SplineSketch --points "0,0;10,20;30,10;40,30" --closed
fc sketch close SplineSketch
```

### 关键注意事项
- `--elements` 使用 0 基索引
- `--points` 使用分号分隔的 `x,y` 坐标对
- `add-polygon` 的 `--radius` 是外接圆半径
- `sketch export` 导出为 DXF 格式

---

## 3. body 命令组（20 个）

> PartDesign 工作台：Body 管理、凸台/凹槽、阵列、孔、抽壳、拔模、基准特征。

| 命令 | 说明 |
|------|------|
| `body new/list/get` | 创建/列出/获取 Body |
| `body pad/pocket <body> <sketch>` | 凸台/凹槽（拉伸/拉伸切割）|
| `body fillet/chamfer <body>` | 圆角/倒角 |
| `body revolution/groove <body> <sketch>` | 旋转凸台/旋转凹槽 |
| `body pattern-linear/polar/mirror <body> <feature>` | 线性/圆周/镜像阵列 |
| `body hole <body> <sketch>` | 孔特征 |
| `body shell/draft <body>` | 抽壳/拔模斜度 |
| `body datum-plane/point/line <body>` | 基准面/点/线 |
| `body set-tip/remove-feature <body>` | 设置 Tip/移除特征 |

### PartDesign 核心概念

- **Body**：参数化建模的核心容器，包含有序的 Feature 链
- **Tip**：当前活跃特征，新操作在 Tip 之后添加
- **Feature 顺序**：特征按添加顺序执行，顺序影响最终结果
- **基准特征（Datum）**：参考几何，不产生实体，为其他特征提供参考

### 典型工作流

**参数化法兰盘（sketch → pad → hole → pattern）：**
```bash
fc body new --name FlangeBody
# 创建草图 FlangeSketch: circle r=50 → close → pad
fc body pad FlangeBody FlangeSketch --length 10
# 创建草图 HoleSketch: circle r=3 @ (35,0) → close → hole
fc body hole FlangeBody HoleSketch --diameter 6 --depth 10
fc body pattern-polar FlangeBody Hole --count 6 --angle 360
```

**带拔模的壳体（pad → shell → draft）：**
```bash
fc body new --name HousingBody
# sketch: rect 100x80 → pad 50 → shell → draft
fc body pad HousingBody BaseSketch --length 50
fc body shell HousingBody --thickness 3 --faces 0
fc body draft HousingBody --angle 3 --faces 1,2,3,4
```

**基准面偏移特征（datum-plane → sketch → pad）：**
```bash
fc body new --name MainBody
fc body pad MainBody BaseSketch --length 20
fc body datum-plane MainBody --name TopPlane --plane XY --offset 20
# 在偏移 20mm 的草图上画圆 → pad 15
fc body pad MainBody TopSketch --length 15
```

**线性阵列（pad → pocket → pattern-linear）：**
```bash
fc body new --name BracketBody
fc body pad BracketBody BaseSketch --length 10
fc body pocket BracketBody SlotSketch --length 10
fc body pattern-linear BracketBody Pocket --direction X --count 4 --spacing 12
```

### 关键注意事项
- `--length` 单位为 mm
- `--spacing` 是相邻实例间的距离
- `--angle` 单位为度（pattern-polar 中 360 = 完整圆周）
- `body shell` 的 `--faces` 是要移除的面索引（逗号分隔）
- `body set-tip` 不指定 `--feature` 时自动设为最后一个特征
- `body remove-feature` 移除特征后，后续特征可能受影响

---

## 4. 建模模式

### 模式 1：基元 + 孔（Base + Hole）
```bash
fc part add box      --name Base -P Length=100 -P Width=80 -P Height=10
fc part add cylinder --name Hole -P Radius=5   -P Height=15
fc part boolean cut Base Hole --name Result
```

### 模式 2：草图 → 凸台 → 特征（Sketch → Pad → Features）
```bash
fc sketch new --name Profile --plane XY
fc sketch add-rect Profile --corner 0,0 --width 60 --height 40
fc sketch close Profile
fc body new --name MyBody
fc body pad MyBody Profile --length 20
fc sketch new --name CutProfile --plane XY
fc sketch add-circle CutProfile --center 30,20 --radius 8
fc sketch close CutProfile
fc body pocket MyBody CutProfile --length 20
fc body fillet MyBody --radius 3 --edges all
```

### 模式 3：多实体（Multi-body）
```bash
fc part add box      --name Base -P Length=50 -P Width=50 -P Height=10
fc part add cylinder --name Post -P Radius=10 -P Height=40 --position 25,25,10
fc part boolean fuse Base Post --name Assembly
```

### 模式 4：阵列/模式（Pattern/Array）
```bash
fc body new --name PatternBody
fc sketch new --name PadSketch --plane XY
fc sketch add-rect PadSketch --corner 0,0 --width 60 --height 40
fc sketch close PadSketch
fc body pad PatternBody PadSketch --length 10
fc sketch new --name HoleSketch --plane XY
fc sketch add-circle HoleSketch --center 10,10 --radius 5
fc sketch close HoleSketch
fc body pocket PatternBody HoleSketch --length 10
fc body pattern-linear PatternBody Pocket --direction X --count 4 --spacing 12
fc body pattern-polar PatternBody Pocket --count 6 --angle 360
```
