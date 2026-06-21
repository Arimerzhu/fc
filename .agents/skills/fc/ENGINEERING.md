---
name: fc-engineering
description: fc 工程技能 — assembly/fem/cam/material 命令组。工程分析/装配时加载。
---

# fc-engineering — 工程分析命令组

涵盖装配、有限元分析、CAM 加工、材料管理四大工程命令组。

## 1. Assembly 装配（12 命令）

| 命令 | 说明 |
|------|------|
| `assembly create` | 创建装配（a2plus/a4/asm3）|
| `assembly add` | 添加部件 |
| `assembly remove` | 移除部件 |
| `assembly constraint` | 添加约束 |
| `assembly solve` | 求解约束 |
| `assembly explode` | 爆炸视图 |
| `assembly animate` | 创建动画 |
| `assembly list` | 列出部件 |
| `assembly ground` | 固定部件 |
| `assembly show` | 显示装配树 |
| `assembly interference` | 干涉检查 |
| `assembly bom` | 物料清单（可输出 CSV）|

### 典型工作流：基本装配
```bash
fc assembly create --name MainAssembly
fc assembly add --assembly MainAssembly --object Shaft
fc assembly add --assembly MainAssembly --object Bearing
fc assembly constraint --type coincident --obj1 Shaft --obj2 Bearing
fc assembly solve
```

### 典型工作流：干涉检查 + BOM
```bash
fc assembly interference
fc assembly bom --output bom.csv
```

> **注意**：constraint 支持 coincident/parallel/perpendicular/distance/angle/axial/plane。

## 2. FEM 有限元分析（11 命令）

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
| `fem result-export` | 结果导出（csv/vtk/vtu）|

### 典型工作流：静力分析
```bash
fem analysis --name StaticAnalysis
fem mesh --analysis StaticAnalysis --object Beam --max-size 5
fem material --analysis StaticAnalysis --material Steel --object Beam
fem constraint --analysis StaticAnalysis --type fixed --object Beam
fem solve --analysis StaticAnalysis --solver calculix
fem result --analysis StaticAnalysis
```

### 典型工作流：梁分析 + 结果导出
```bash
fem beam-section --analysis StaticAnalysis --object Beam --type rectangular --width 10 --height 10
fem solve --analysis StaticAnalysis
fem result-filter --analysis StaticAnalysis --type maximum
fem result-export --analysis StaticAnalysis --output results.json
```

> **注意**：constraint 支持 fixed/force/pressure/displacement/temperature/gravity；求解器支持 calculix/elmer/z88。

## 3. CAM 加工（10 命令）

| 命令 | 说明 |
|------|------|
| `cam job` | 创建 CAM 任务 |
| `cam tool` | 定义刀具 |
| `cam toolpath` | 生成刀路 |
| `cam postprocess` | 后处理为 G 代码 |
| `cam simulate` | 仿真刀路 |
| `cam list` | 列出 CAM 对象 |
| `cam show` | 显示任务详情 |
| `cam setup-sheet` | 创建设置表 |
| `cam inspect` | 检查刀路 |
| `cam verify` | 验证刀路 |

### 典型工作流：基本铣削
```bash
fc cam job --name MyJob --model Stock
fc cam tool --name EndMill6 --type endmill --diameter 6 --speed 12000 --feed 1000
fc cam toolpath --job MyJob --type profile --depth 5 --step-down 2
fc cam simulate --job MyJob
fc cam postprocess --job MyJob --output part.nc
```

> **注意**：toolpath 支持 profile/pocket/drill/engrave/adaptive/helix/slot/3d_pocket；verify 可检查 gouge 和 collision。

## 4. Material 材料管理（9 命令）

| 命令 | 说明 |
|------|------|
| `material list` | 列出材料（可指定库）|
| `material show` | 显示材料属性 |
| `material assign` | 分配材料到对象 |
| `material create` | 创建自定义材料 |
| `material edit` | 编辑材料属性 |
| `material remove` | 删除材料 |
| `material library` | 列出材料库 |
| `material export` | 导出材料卡片 |
| `material import` | 导入材料卡片 |

### 典型工作流
```bash
fc material list --library Standard
fc material create --name MS --density 7850 --youngs-modulus 210000 --poisson-ratio 0.3
fc material assign --object Beam --material MS
fc material export MS --output ms.json
```

---

## 完整工程工作流

### FEM 分析管道
```
创建模型 → fem analysis → fem mesh → fem material → fem constraint
  → fem solve → fem result → fem result-filter → fem result-export
```

### 装配管道
```
创建装配 → assembly create → 添加部件 → assembly add (多次)
  → 添加约束 → assembly constraint (多次) → assembly solve
  → [assembly interference] → [assembly bom]
```

> 所有命令支持 `--json` 输出，便于 Agent 自动化处理。
