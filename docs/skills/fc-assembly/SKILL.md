---
name: fc-assembly
description: FreeCAD 装配命令 — 创建/添加/移除/约束/求解/爆炸/动画/列表/固定/显示/干涉检查/BOM。用于多部件装配。
---

# fc-assembly — FreeCAD 装配 CLI 命令

## 命令组概览（12 个命令）

| 命令 | 说明 |
|------|------|
| `assembly create` | 创建装配 |
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
| `assembly bom` | 物料清单 |

## 典型工作流

### 工作流 1：基本装配
```bash
fc document new --name MyAssembly
fc assembly create --name MainAssembly
fc part add cylinder --name Shaft -P Radius=5 -P Height=50
fc part add cylinder --name Bearing -P Radius=8 -P Height=15
fc assembly add --assembly MainAssembly --object Shaft
fc assembly add --assembly MainAssembly --object Bearing
fc assembly constraint --type coincident --obj1 Shaft --obj2 Bearing
fc assembly solve
```

### 工作流 2：干涉检查 + BOM
```bash
fc assembly interference
fc assembly bom --output bom.csv
```

## 注意事项

- 所有命令支持 `--json` 输出
- `assembly create` 支持 a2plus/a4/asm3 装配类型
- `assembly constraint` 支持 coincident/parallel/perpendicular/distance/angle/axial/plane
- `assembly interference` 不指定对象时检查所有部件对
- `assembly bom` 可输出 CSV 文件
