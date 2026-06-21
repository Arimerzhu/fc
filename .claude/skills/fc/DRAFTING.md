---
name: fc-drafting
description: fc 出图技能 — techdraw/draft/spreadsheet 命令组。出图/标注时加载。
---

# fc-drafting — 出图与文档命令组

涵盖 TechDraw 工程图、Draft 2D/3D 绘图、电子表格三大命令组。

## 1. TechDraw 工程图（14 命令）

| 命令 | 说明 |
|------|------|
| `techdraw page` | 创建图纸页面（A4/A3/A2 等）|
| `techdraw view` | 添加视图到页面 |
| `techdraw dimension` | 添加尺寸标注 |
| `techdraw annotation` | 添加注释文本 |
| `techdraw symbol` | 添加符号 |
| `techdraw export` | 导出页面（SVG/PDF）|
| `techdraw list` | 列出所有页面 |
| `techdraw get` | 获取页面详情 |
| `techdraw section` | 创建剖面视图 |
| `techdraw detail` | 创建局部放大视图 |
| `techdraw centerline` | 添加中心线 |
| `techdraw hatch` | 添加剖面线 |
| `techdraw table` | 创建 BOM 表 |
| `techdraw delete-view` | 删除视图 |

### 典型工作流：基本工程图
```bash
fc techdraw page --name MainPage --format A3
fc techdraw view --page MainPage --source MyModel --name TopView
fc techdraw view --page MainPage --source MyModel --name SideView --direction 1,0,0
fc techdraw dimension --view TopView --type distance --elements 0,1
fc techdraw annotation --page MainPage --text "Parts List v1.0" --position 10,10
fc techdraw export MainPage --output drawing.pdf
```

### 典型工作流：剖面 + BOM
```bash
fc techdraw section --page MainPage --source SideView --direction horizontal --position 0,50,0
fc techdraw hatch --page MainPage --view SectionView --pattern ANSI31 --scale 0.5
fc techdraw table --page MainPage --position 200,10
```

> **注意**：`--direction` 为视图方向矢量；`--position` 为切割面通过点；hatch 颜色格式 `r,g,b`（0-1）；export 自动从扩展名检测格式。

## 2. Draft 2D/3D 绘图（25 命令）

| 类别 | 命令 | 说明 |
|------|------|------|
| 绘图 | `draft line` | 线段 |
| | `draft wire` | 多段线 |
| | `draft circle` | 圆 |
| | `draft arc` | 圆弧 |
| | `draft rect` | 矩形 |
| | `draft polygon` | 正多边形 |
| | `draft text` | 文字 |
| | `draft point` | 点 |
| 标注 | `draft dimension` | 尺寸标注 |
| | `draft label` | 标签 |
| 变换 | `draft move` | 移动 |
| | `draft rotate` | 旋转 |
| | `draft scale` | 缩放 |
| | `draft offset` | 偏移 |
| | `draft mirror` | 镜像 |
| | `draft clone` | 克隆 |
| | `draft stretch` | 拉伸 |
| | `draft trim` | 修剪/延伸 |
| 阵列 | `draft array` | 极坐标/矩形阵列 |
| | `draft path-array` | 路径阵列 |
| | `draft point-array` | 点阵列 |
| 转换 | `draft upgrade` | 升级（线->面->体）|
| | `draft downgrade` | 降级（体->面->线）|
| 其他 | `draft facebinder` | 面绑定器 |
| | `draft list` | 列出 Draft 对象 |
| | `draft svg` | 生成工程图 SVG（独立于 TechDraw）|

### 典型工作流：2D 布局
```bash
fc draft rect --corner 0,0 --width 100 --height 80 --name OuterFrame
fc draft rect --corner 10,10 --width 30 --height 20 --name Window1
fc draft dimension --start 0,0 --end 100,0 --offset 0,-10 --name WidthDim
fc export dxf --output layout.dxf
```

### 典型工作流：路径阵列
```bash
fc draft circle --center 0,0 --radius 5 --name Bolt
fc draft wire --points "0,0,0;50,0,0;50,50,0;0,50,0" --closed --name Path
fc draft path-array Bolt --path Path --count 8
```

> **注意**：array 支持 `polar`（极坐标）和 `rectangular`（矩形）；path-array 沿路径均匀分布；upgrade/downgrade 用于几何层级转换。

### 典型工作流：SVG 工程图（独立于 TechDraw）
```bash
# 从 FCStd 文件生成工程图
fc draft svg --input model.FCStd --output drawing.svg --page A3 --scale 0.5 \
  --title "零件图" --unit "AI Lab" --material "Steel" --drawing-no "DRW-001"

# 从 STEP 文件生成工程图
fc draft svg --input model.step --output drawing.svg --page A4 --views front,top,side

# 从 JSON shape 文件生成工程图
fc draft svg --input shape.json --output drawing.svg --scale 0.3
```

> **注意**：`draft svg` 不依赖 FreeCAD TechDraw 工作bench，使用纯 Python SVG 渲染引擎。支持：
> - 输入格式：`.json`（ShapeData）、`.FCStd`、`.step`、`.stp`
> - 图幅：A0/A1/A2/A3/A4
> - 视图：front/top/side/back/bottom/left/right（自动布局）
> - 标题栏：GB/T 分格样式（单位/标题/设计/审核/材料/比例/重量/数量/图号/版本/日期）

## 3. Spreadsheet 电子表格（11 命令）

| 命令 | 说明 |
|------|------|
| `spreadsheet create` | 创建电子表格 |
| `spreadsheet set` | 设置单元格值 |
| `spreadsheet get` | 获取单元格值 |
| `spreadsheet formula` | 设置公式 |
| `spreadsheet alias` | 设置单元格别名 |
| `spreadsheet link` | 链接到对象属性 |
| `spreadsheet show` | 显示表格内容 |
| `spreadsheet list` | 列出所有表格 |
| `spreadsheet clear` | 清除单元格 |
| `spreadsheet export` | 导出 CSV |
| `spreadsheet import` | 导入 CSV |

### 典型工作流：参数化驱动
```bash
fc spreadsheet create --name Params
fc spreadsheet set --sheet Params --cell A1 --value 100
fc spreadsheet alias --sheet Params --cell A1 --alias Length
fc spreadsheet formula --sheet Params --cell B1 --formula =A1*2
fc spreadsheet link --sheet Params --cell A1 --object Box --property Length
```

---

## 出图管道

```
3D 模型 → techdraw page（创建页面）
  → techdraw view（添加主视图/侧视图/俯视图）
  → techdraw section / detail（剖面/局部视图）
  → techdraw dimension（尺寸标注）
  → techdraw annotation / symbol（注释/符号）
  → techdraw hatch（剖面线）
  → techdraw table（BOM 表）
  → techdraw export（导出 PDF/SVG）
```

> 所有命令支持 `--json` 输出，便于 Agent 自动化处理。
