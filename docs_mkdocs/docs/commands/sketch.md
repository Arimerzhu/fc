---
name: fc-sketch
description: FreeCAD 2D 草图命令 — 几何创建（线/圆/弧/矩形/椭圆/多边形/B 样条/槽/点）、约束、修剪/镜像/克隆/导出。
---

# fc-sketch — FreeCAD 2D 草图 CLI 命令

## 命令组概览（21 个命令）

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
