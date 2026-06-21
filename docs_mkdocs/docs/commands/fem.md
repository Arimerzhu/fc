---
name: fc-fem
description: FreeCAD FEM 有限元分析命令 — 分析创建/网格/材料/约束/求解/结果/梁截面/壳体厚度/结果过滤/结果导出。
---

# fc-fem — FreeCAD FEM 有限元分析 CLI 命令

## 命令组概览（11 个命令）

| 命令 | 说明 |
|------|------|
| `fem analysis` | 创建分析 |
| `fem mesh` | 创建 FEM 网格 |
| `fem material` | 分配材料 |
| `fem constraint` | 添加边界条件 |
| `fem solve` | 运行求解器 |
| `fem result` | 显示结果 |
| `fem list` | 列出分析对象 |
| `fem beam-section` | 梁截面定义 |
| `fem shell-thickness` | 壳体厚度定义 |
| `fem result-filter` | 结果过滤 |
| `fem result-export` | 结果导出 |

## 典型工作流

### 工作流 1：基本静力分析
```bash
fc document new --name Analysis
fc part add box --name Beam -P Length=100 -P Width=10 -P Height=10
fem analysis --name StaticAnalysis
fem mesh --analysis StaticAnalysis --object Beam --max-size 5
fem material --analysis StaticAnalysis --material Steel --object Beam
fem constraint --analysis StaticAnalysis --type fixed --object Beam
fem solve --analysis StaticAnalysis --solver calculix
fem result --analysis StaticAnalysis
```

### 工作流 2：梁分析
```bash
fem beam-section --analysis StaticAnalysis --object Beam --type rectangular --width 10 --height 10
fem solve --analysis StaticAnalysis
fem result-filter --analysis StaticAnalysis --type maximum
fem result-export --analysis StaticAnalysis --output results.json
```

## 注意事项

- 所有命令支持 `--json` 输出
- `fem mesh` 的 `--max-size` 和 `--min-size` 单位为 mm
- `fem constraint` 支持 fixed/force/pressure/displacement/temperature/gravity
- `fem solve` 支持 calculix/elmer/z88 求解器
- `fem result-export` 支持 csv/vtk/vtu 格式
