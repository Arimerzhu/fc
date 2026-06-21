---
name: fc-techdraw
description: FreeCAD TechDraw 工作台命令 — 页面/视图/标注/剖面/细节/中心线/剖面线/表格/符号/导出。用于创建工程图。
---

# fc-techdraw — FreeCAD TechDraw 工作台 CLI 命令

## 命令组概览（14 个命令）

| 命令 | 说明 |
|------|------|
| `techdraw page` | 创建新图纸页面 |
| `techdraw view` | 添加视图到页面 |
| `techdraw dimension` | 添加标注 |
| `techdraw annotation` | 添加注释文本 |
| `techdraw symbol` | 添加符号 |
| `techdraw export` | 导出页面 (SVG/PDF) |
| `techdraw list` | 列出所有页面 |
| `techdraw get` | 获取页面详情 |
| `techdraw section` | 创建剖面视图 |
| `techdraw detail` | 创建局部视图 |
| `techdraw centerline` | 添加中心线 |
| `techdraw hatch` | 添加剖面线 |
| `techdraw table` | 创建 BOM 表 |
| `techdraw delete-view` | 删除视图 |

## 典型工作流

### 工作流 1：创建基本工程图
```bash
fc techdraw page --name MainPage --format A3
fc techdraw view --page MainPage --source MyModel --name TopView
fc techdraw view --page MainPage --source MyModel --name SideView --direction 1,0,0
fc techdraw dimension --view TopView --type distance --elements 0,1
fc techdraw annotation --page MainPage --text "Parts List v1.0" --position 10,10
fc techdraw export MainPage --output drawing.pdf
```

### 工作流 2：剖面视图 + BOM
```bash
fc techdraw section --page MainPage --source SideView --direction horizontal --position 0,50,0
fc techdraw hatch --page MainPage --view SectionView --pattern ANSI31 --scale 0.5
fc techdraw table --page MainPage --position 200,10
```

### 工作流 3：细节视图
```bash
fc techdraw detail --page MainPage --source TopView --center 25,25,0 --radius 5 --scale 3
```

## 注意事项

- 所有命令支持 `--json` 输出
- `techdraw view` 的 `--direction` 是视图方向矢量
- `techdraw section` 的 `--position` 是切割面通过点
- `techdraw hatch` 的颜色格式是 `r,g,b` 0-1
- `techdraw export` 自动从输出文件扩展名检测格式
