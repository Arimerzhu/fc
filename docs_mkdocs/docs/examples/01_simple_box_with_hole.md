# 示例 1：简单底板通孔

**难度**: 简单
**命令组**: document, part, export
**步骤数**: 7

## 需求

创建一个 100x100x10 的底板，在底板中心打一个直径 20 的通孔。

## 阶段1: 工具选型

| 命令组 | 命令 | 用途 |
|--------|------|------|
| document | `document new` | 创建新文档 |
| part | `part add box` | 创建底板立方体 |
| part | `part add cylinder` | 创建通孔圆柱体 |
| part | `part boolean cut` | 从底板中减去圆柱形成通孔 |
| export | `export step` | 导出 STEP 文件 |
| document | `document save` | 保存项目文件 |

## 阶段2: 任务拆解

1. 创建新文档 `PlateDoc`
2. 创建底板立方体 `BasePlate`：100x100x10，中心位于原点
3. 创建通孔圆柱体 `HoleCyl`：直径 20（半径 10），高度 15（确保穿透），中心位于底板顶面中心
4. 执行布尔差集 `CutResult` = BasePlate - HoleCyl
5. 导出 STEP 文件
6. 保存项目文件

## 阶段3: 坐标与依赖计算

### 步骤 1：创建文档
- 无依赖
- 文档名: `PlateDoc`

### 步骤 2：创建底板立方体
- 依赖: 文档已创建
- 中心位置: `0, 0, 5`（底板厚 10，底面在 Z=0，中心在 Z=5）
- 参数: Length=100, Width=100, Height=10
- 名称: `BasePlate`

### 步骤 3：创建通孔圆柱体
- 依赖: 底板已创建
- 中心位置: `0, 0, 5`（圆柱体中心与底板中心对齐，Z=5 确保上下穿透）
- 参数: Radius=10, Height=15（大于底板厚度 10，确保完全穿透）
- 名称: `HoleCyl`

### 步骤 4：布尔差集
- 依赖: `BasePlate`, `HoleCyl`
- 操作: `cut`（从底板中减去圆柱）
- 结果名: `PlateWithHole`

### 步骤 5：导出 STEP
- 依赖: `PlateWithHole`
- 输出路径: `plate_with_hole.step`

### 步骤 6：保存项目
- 依赖: 所有操作完成
- 输出路径: `plate_with_hole.FCStd`

## 阶段4: 依赖校验

| 步骤 | 依赖 | 状态 |
|------|------|------|
| 1. document new | 无 | 合法 |
| 2. part add box (BasePlate) | 文档存在 | 合法 |
| 3. part add cylinder (HoleCyl) | 文档存在 | 合法 |
| 4. part boolean cut | BasePlate, HoleCyl 已创建 | 合法 |
| 5. export step | PlateWithHole 已创建 | 合法 |
| 6. document save | 所有操作完成 | 合法 |

所有依赖关系正确，无循环依赖。

## 阶段5: 命令输出

```bash
# 1. 创建新文档
fc document new --name PlateDoc --json

# 2. 创建底板立方体（中心在 Z=5，底面在 Z=0）
fc part add box --name BasePlate --position 0,0,5 --param Length=100 --param Width=100 --param Height=10 --json

# 3. 创建通孔圆柱体（半径 10，高度 15 确保穿透）
fc part add cylinder --name HoleCyl --position 0,0,5 --param Radius=10 --param Height=15 --json

# 4. 布尔差集：底板减去圆柱形成通孔
fc part boolean cut --base BasePlate --tool HoleCyl --name PlateWithHole --json

# 5. 导出 STEP 文件
fc export step --output plate_with_hole.step --overwrite --json

# 6. 保存项目文件
fc document save --output plate_with_hole.FCStd --json
```

## 完整命令序列

```bash
fc document new --name PlateDoc --json
fc part add box --name BasePlate --position 0,0,5 --param Length=100 --param Width=100 --param Height=10 --json
fc part add cylinder --name HoleCyl --position 0,0,5 --param Radius=10 --param Height=15 --json
fc part boolean cut --base BasePlate --tool HoleCyl --name PlateWithHole --json
fc export step --output plate_with_hole.step --overwrite --json
fc document save --output plate_with_hole.FCStd --json
```

## 预期输出

```json
// 1. document new
{"status": "ok", "operation": "document_new", "data": {"name": "PlateDoc"}, "message": "Document 'PlateDoc' created"}

// 2. part add box
{"status": "ok", "operation": "part_add", "data": {"name": "BasePlate", "type": "box"}, "message": "Primitive 'BasePlate' created"}

// 3. part add cylinder
{"status": "ok", "operation": "part_add", "data": {"name": "HoleCyl", "type": "cylinder"}, "message": "Primitive 'HoleCyl' created"}

// 4. part boolean cut
{"status": "ok", "operation": "part_boolean", "data": {"result": "PlateWithHole"}, "message": "Boolean CUT completed: 'PlateWithHole'"}

// 5. export step
{"status": "ok", "operation": "export_step", "data": {"file": "plate_with_hole.step", "size": 15234}, "message": "Exported to plate_with_hole.step"}

// 6. document save
{"status": "ok", "operation": "document_save", "data": {"path": "plate_with_hole.FCStd"}, "message": "Saved to plate_with_hole.FCStd"}
```
