---
name: fc-draft
description: FreeCAD Draft 工作台命令 — 2D/3D 绘图、标注、阵列、变换、升级/降级、路径阵列、标签。
---

# fc-draft — FreeCAD Draft 工作台 CLI 命令

## 命令组概览（25 个命令）

| 命令 | 说明 |
|------|------|
| `draft line` | 创建线段 |
| `draft wire` | 创建多段线 |
| `draft circle` | 创建圆 |
| `draft arc` | 创建圆弧 |
| `draft rect` | 创建矩形 |
| `draft polygon` | 创建正多边形 |
| `draft text` | 创建文字 |
| `draft dimension` | 创建标注 |
| `draft array` | 阵列（极坐标/矩形）|
| `draft offset` | 偏移 |
| `draft move` | 移动 |
| `draft rotate` | 旋转 |
| `draft scale` | 缩放 |
| `draft trim` | 修剪/延伸 |
| `draft clone` | 克隆 |
| `draft mirror` | 镜像 |
| `draft stretch` | 拉伸 |
| `draft upgrade` | 升级（线->面->体）|
| `draft downgrade` | 降级（体->面->线）|
| `draft path-array` | 路径阵列 |
| `draft point-array` | 点阵列 |
| `draft point` | 创建点 |
| `draft facebinder` | 面绑定器 |
| `draft label` | 标签 |
| `draft list` | 列出 Draft 对象 |

## 典型工作流

### 工作流 1：2D 工程布局
```bash
fc document new --name Layout
fc draft rect --corner 0,0 --width 100 --height 80 --name OuterFrame
fc draft rect --corner 10,10 --width 30 --height 20 --name Window1
fc draft rect --corner 60,10 --width 30 --height 20 --name Window2
fc draft dimension --start 0,0 --end 100,0 --offset 0,-10 --name WidthDim
fc export dxf --output layout.dxf
```

### 工作流 2：路径阵列
```bash
fc draft circle --center 0,0 --radius 5 --name Bolt
fc draft wire --points "0,0,0;50,0,0;50,50,0;0,50,0" --closed --name Path
fc draft path-array Bolt --path Path --count 8
```

### 工作流 3：升级和降级
```bash
fc draft wire --points "0,0,0;10,0,0;10,10,0;0,10,0" --closed --name Profile
fc draft upgrade Profile --name ProfileFace
fc draft downgrade ProfileFace --name ProfileEdges
```

## 注意事项

- 所有命令支持 `--json` 输出
- `draft array` 支持 `polar`（极坐标）和 `rectangular`（矩形）两种类型
- `draft path-array` 沿路径均匀分布对象
- `draft upgrade` 尝试将低级几何升级为高级几何
- `draft downgrade` 将高级几何分解为低级几何
