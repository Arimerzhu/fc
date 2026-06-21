---
name: fc-surface
description: FreeCAD 曲面操作命令 — 放样/扫描/填充/管道/偏移/加厚/展平/缝合/拉伸/旋转/直纹/曲率分析。
---

# fc-surface — FreeCAD 曲面操作 CLI 命令

## 命令组概览（13 个命令）

| 命令 | 说明 |
|------|------|
| `surface loft` | 放样曲面 |
| `surface sweep` | 扫描曲面 |
| `surface fill` | 填充曲面 |
| `surface pipe` | 管道曲面 |
| `surface offset` | 偏移曲面 |
| `surface thicken` | 加厚曲面 |
| `surface flatten` | 展平曲面 |
| `surface sew` | 缝合曲面 |
| `surface extrude` | 拉伸曲面 |
| `surface revolve` | 旋转曲面 |
| `surface ruled` | 直纹曲面 |
| `surface curvature` | 曲率分析 |
| `surface list` | 列出曲面对象 |

## 典型工作流

### 工作流 1：放样曲面
```bash
fc document new --name LoftSurf
fc sketch new --name Profile1 --plane XY
fc sketch add-circle Profile1 --center 0,0 --radius 10
fc sketch close Profile1
fc sketch new --name Profile2 --plane XY --offset 20
fc sketch add-circle Profile2 --center 0,0 --radius 15
fc sketch close Profile2
fc surface loft --profiles "Profile1;Profile2" --solid
fc export step --output loft_surf.step
```

### 工作流 2：管道曲面
```bash
fc document new --name PipeSurf
fc sketch new --name PathSketch --plane XY
fc sketch add-arc PathSketch --center 0,0 --radius 20 --start-angle 0 --end-angle 180
fc sketch close PathSketch
fc surface pipe --path PathSketch --radius 3
fc export step --output pipe_surf.step
```

### 工作流 3：加厚曲面
```bash
fc surface thicken Loft --thickness 2 --direction both
fc export step --output thickened.step
```

## 注意事项

- 所有命令支持 `--json` 输出
- `surface loft` 需要至少 2 个轮廓
- `surface thicken` 的 `--direction` 可以是 `both` 或 `single`
- `surface curvature` 分析指定面的曲率信息
