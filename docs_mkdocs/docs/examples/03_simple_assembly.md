# 示例 3：简单装配体

**难度**: 中等
**命令组**: document, part, assembly, export
**步骤数**: 14

## 需求

创建一个简单装配体：底座板 100x100x5，上面安装 4 个直径 8 高 30 的圆柱支柱，支柱间距 60mm。

## 阶段1: 工具选型

| 命令组 | 命令 | 用途 |
|--------|------|------|
| document | `document new` | 创建新文档 |
| part | `part add box` | 创建底座板 |
| part | `part add cylinder` | 创建单个圆柱支柱 |
| part | `part copy` | 复制支柱到 4 个位置 |
| part | `part transform` | 移动支柱到正确位置 |
| assembly | `assembly create` | 创建装配体 |
| assembly | `assembly add` | 添加底座和支柱到装配体 |
| assembly | `assembly ground` | 固定底座 |
| assembly | `assembly constraint` | 添加约束 |
| assembly | `assembly solve` | 求解装配 |
| export | `export step` | 导出装配体 |

## 阶段2: 任务拆解

1. 创建新文档 `AssemblyDoc`
2. 创建底座板 `BasePlate`：100x100x5，中心在 `0,0,2.5`
3. 创建单个支柱 `Pillar`：直径 8（半径 4），高 30
4. 复制支柱到 4 个位置：`Pillar1`(-30,-30), `Pillar2`(-30,30), `Pillar3`(30,-30), `Pillar4`(30,30)
5. 创建装配体 `MainAssembly`
6. 添加底座板到装配体
7. 添加 4 个支柱到装配体
8. 固定底座板（Ground）
9. 为每个支柱添加面重合约束（支柱底面与底座顶面）
10. 求解装配
11. 导出 STEP 文件

## 阶段3: 坐标与依赖计算

### 底座板几何
- 尺寸: 100x100x5
- 中心位置: `0, 0, 2.5`（底面在 Z=0，顶面在 Z=5）
- 支柱间距: 60mm（从中心测量）
- 支柱位置: (-30,-30), (-30,30), (30,-30), (30,30)

### 支柱几何
- 直径: 8mm（半径 4mm）
- 高度: 30mm
- 第一个支柱位置: `0, 0, 5`（底面贴合底座顶面 Z=5）
- 复制后通过 transform 移动到目标位置

### 步骤依赖

| 步骤 | 操作 | 依赖元素 | 输出元素 |
|------|------|----------|----------|
| 1 | document new | 无 | `AssemblyDoc` |
| 2 | part add box | 文档 | `BasePlate` |
| 3 | part add cylinder | 文档 | `Pillar` |
| 4 | part copy x4 | `Pillar` | `Pillar1`~`Pillar4` |
| 5 | part transform x4 | `Pillar1`~`Pillar4` | 位置更新 |
| 6 | assembly create | 文档 | `MainAssembly` |
| 7 | assembly add x5 | `MainAssembly`, 所有部件 | - |
| 8 | assembly ground | `MainAssembly`, `BasePlate` | - |
| 9 | assembly constraint x4 | 支柱, 底座 | - |
| 10 | assembly solve | `MainAssembly` | - |
| 11 | export step | 所有完成 | 文件 |

### 支柱位置计算

底座板顶面 Z=5，支柱高 30，支柱中心 Z = 5 + 15 = 20。

| 支柱 | X | Y | Z |
|------|---|---|---|
| Pillar1 | -30 | -30 | 20 |
| Pillar2 | -30 | 30 | 20 |
| Pillar3 | 30 | -30 | 20 |
| Pillar4 | 30 | 30 | 20 |

## 阶段4: 依赖校验

- 底座板创建后才能创建装配体
- 所有部件创建后才能添加到装配体
- Ground 操作必须在约束之前
- 约束操作必须在 solve 之前
- 所有依赖关系正确，无循环依赖

## 阶段5: 命令输出

```bash
# 1. 创建新文档
fc document new --name AssemblyDoc --json

# 2. 创建底座板（100x100x5，中心在 Z=2.5）
fc part add box --name BasePlate --position 0,0,2.5 --param Length=100 --param Width=100 --param Height=5 --json

# 3. 创建单个支柱（直径 8，高 30，底面在 Z=5）
fc part add cylinder --name Pillar --position 0,0,20 --param Radius=4 --param Height=30 --json

# 4. 复制支柱为 4 个实例
fc part copy Pillar --name Pillar1 --json
fc part copy Pillar --name Pillar2 --json
fc part copy Pillar --name Pillar3 --json
fc part copy Pillar --name Pillar4 --json

# 5. 移动支柱到四个角位置（间距 60mm）
fc part transform Pillar1 --position -30,-30,20 --json
fc part transform Pillar2 --position -30,30,20 --json
fc part transform Pillar3 --position 30,-30,20 --json
fc part transform Pillar4 --position 30,30,20 --json

# 6. 创建装配体
fc assembly create --name MainAssembly --json

# 7. 添加所有部件到装配体
fc assembly add --assembly MainAssembly --object BasePlate --json
fc assembly add --assembly MainAssembly --object Pillar1 --json
fc assembly add --assembly MainAssembly --object Pillar2 --json
fc assembly add --assembly MainAssembly --object Pillar3 --json
fc assembly add --assembly MainAssembly --object Pillar4 --json

# 8. 固定底座板
fc assembly ground --assembly MainAssembly --object BasePlate --json

# 9. 添加面重合约束（每个支柱底面贴合底座顶面）
fc assembly constraint --type coincident --obj1 BasePlate --obj2 Pillar1 --json
fc assembly constraint --type coincident --obj1 BasePlate --obj2 Pillar2 --json
fc assembly constraint --type coincident --obj1 BasePlate --obj2 Pillar3 --json
fc assembly constraint --type coincident --obj1 BasePlate --obj2 Pillar4 --json

# 10. 求解装配
fc assembly solve --assembly MainAssembly --json

# 11. 导出装配体
fc export step --output simple_assembly.step --overwrite --json
```

## 完整命令序列

```bash
fc document new --name AssemblyDoc --json
fc part add box --name BasePlate --position 0,0,2.5 --param Length=100 --param Width=100 --param Height=5 --json
fc part add cylinder --name Pillar --position 0,0,20 --param Radius=4 --param Height=30 --json
fc part copy Pillar --name Pillar1 --json
fc part copy Pillar --name Pillar2 --json
fc part copy Pillar --name Pillar3 --json
fc part copy Pillar --name Pillar4 --json
fc part transform Pillar1 --position -30,-30,20 --json
fc part transform Pillar2 --position -30,30,20 --json
fc part transform Pillar3 --position 30,-30,20 --json
fc part transform Pillar4 --position 30,30,20 --json
fc assembly create --name MainAssembly --json
fc assembly add --assembly MainAssembly --object BasePlate --json
fc assembly add --assembly MainAssembly --object Pillar1 --json
fc assembly add --assembly MainAssembly --object Pillar2 --json
fc assembly add --assembly MainAssembly --object Pillar3 --json
fc assembly add --assembly MainAssembly --object Pillar4 --json
fc assembly ground --assembly MainAssembly --object BasePlate --json
fc assembly constraint --type coincident --obj1 BasePlate --obj2 Pillar1 --json
fc assembly constraint --type coincident --obj1 BasePlate --obj2 Pillar2 --json
fc assembly constraint --type coincident --obj1 BasePlate --obj2 Pillar3 --json
fc assembly constraint --type coincident --obj1 BasePlate --obj2 Pillar4 --json
fc assembly solve --assembly MainAssembly --json
fc export step --output simple_assembly.step --overwrite --json
```

## 预期输出

```json
// 1. document new
{"status": "ok", "operation": "document_new", "data": {"name": "AssemblyDoc"}, "message": "Document 'AssemblyDoc' created"}

// 2. part add box
{"status": "ok", "operation": "part_add", "data": {"name": "BasePlate", "type": "box"}, "message": "Primitive 'BasePlate' created"}

// 3. part add cylinder
{"status": "ok", "operation": "part_add", "data": {"name": "Pillar", "type": "cylinder"}, "message": "Primitive 'Pillar' created"}

// 4. part copy x4
{"status": "ok", "operation": "part_copy", "data": {"new_name": "Pillar1"}, "message": "Copied to 'Pillar1'"}
{"status": "ok", "operation": "part_copy", "data": {"new_name": "Pillar2"}, "message": "Copied to 'Pillar2'"}
{"status": "ok", "operation": "part_copy", "data": {"new_name": "Pillar3"}, "message": "Copied to 'Pillar3'"}
{"status": "ok", "operation": "part_copy", "data": {"new_name": "Pillar4"}, "message": "Copied to 'Pillar4'"}

// 5. part transform x4
{"status": "ok", "operation": "part_transform", "data": {"status": "moved"}, "message": "Pillar1 moved to -30,-30,20"}
{"status": "ok", "operation": "part_transform", "data": {"status": "moved"}, "message": "Pillar2 moved to -30,30,20"}
{"status": "ok", "operation": "part_transform", "data": {"status": "moved"}, "message": "Pillar3 moved to 30,-30,20"}
{"status": "ok", "operation": "part_transform", "data": {"status": "moved"}, "message": "Pillar4 moved to 30,30,20"}

// 6. assembly create
{"status": "ok", "operation": "assembly_create", "data": {"name": "MainAssembly"}, "message": "Assembly 'MainAssembly' created"}

// 7. assembly add x5
{"status": "ok", "operation": "assembly_add", "data": {"status": "added"}, "message": "BasePlate added to MainAssembly"}
{"status": "ok", "operation": "assembly_add", "data": {"status": "added"}, "message": "Pillar1 added to MainAssembly"}
{"status": "ok", "operation": "assembly_add", "data": {"status": "added"}, "message": "Pillar2 added to MainAssembly"}
{"status": "ok", "operation": "assembly_add", "data": {"status": "added"}, "message": "Pillar3 added to MainAssembly"}
{"status": "ok", "operation": "assembly_add", "data": {"status": "added"}, "message": "Pillar4 added to MainAssembly"}

// 8. assembly ground
{"status": "ok", "operation": "assembly_ground", "data": {"status": "grounded"}, "message": "BasePlate grounded"}

// 9. assembly constraint x4
{"status": "ok", "operation": "assembly_constraint", "data": {"type": "coincident"}, "message": "Constraint added: BasePlate <-> Pillar1"}
{"status": "ok", "operation": "assembly_constraint", "data": {"type": "coincident"}, "message": "Constraint added: BasePlate <-> Pillar2"}
{"status": "ok", "operation": "assembly_constraint", "data": {"type": "coincident"}, "message": "Constraint added: BasePlate <-> Pillar3"}
{"status": "ok", "operation": "assembly_constraint", "data": {"type": "coincident"}, "message": "Constraint added: BasePlate <-> Pillar4"}

// 10. assembly solve
{"status": "ok", "operation": "assembly_solve", "data": {"status": "solved"}, "message": "Assembly solved successfully"}

// 11. export step
{"status": "ok", "operation": "export_step", "data": {"file": "simple_assembly.step", "size": 45678}, "message": "Exported to simple_assembly.step"}
```
