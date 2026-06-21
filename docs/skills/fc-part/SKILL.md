---
name: fc-part
description: FreeCAD Part 工作台命令 — 3D 基元创建、布尔操作、变换、倒角/圆角、孔。用于创建和管理基础 3D 几何体。
---

# fc-part — FreeCAD Part 工作台 CLI 命令

## 命令组概览（14 个命令）

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

### spiral（螺旋线）
```
fc part add spiral --name MySpiral
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

### 工作流 3：使用 part hole 打孔
```bash
fc document new --name Plate
fc part add box --name BasePlate -P Length=100 -P Width=80 -P Height=10
fc part hole BasePlate --diameter 8 --depth 10 --position 25,25,0
fc part hole BasePlate --diameter 8 --depth 10 --position 75,25,0
fc part hole BasePlate --diameter 8 --depth 10 --position 25,55,0
fc part hole BasePlate --diameter 8 --depth 10 --position 75,55,0
fc export step --output plate.step
```

## 注意事项

- 所有命令支持 `--json` 输出
- `part add` 的 `--param/-P` 接受 `key=value` 格式，可重复
- `part boolean` 操作后原始对象保留，结果为新对象
- `part fillet-3d` 和 `part chamfer-3d` 的 `--edges` 可以是 `all` 或逗号分隔的索引
- `part scale` 的 factor 可以是单个数字（均匀）或 `x,y,z`（非均匀）
- `part hole` 在实体内部创建一个圆柱体并与原实体做 cut 操作
