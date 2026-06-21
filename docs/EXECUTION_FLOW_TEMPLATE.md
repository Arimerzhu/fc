# 五阶段执行流模板 — AI Agent 使用指南

> 本文件定义了 AI Agent 使用 FreeCAD CLI 进行 CAD 建模时必须遵循的五阶段执行流。
> 参考工程化方案设计，确保 AI 从 "会写命令" 升级为 "会用工具"。

---

## 核心原则

**违反任何一条规则都视为错误，必须重新生成。**

1. 只能使用 FreeCAD CLI 命令，禁止使用任何未列出的命令
2. 所有元素必须指定唯一名称，格式：`{类型}_{序号}`（如 `Box_001`、`Cylinder_001`）
3. 后续命令只能引用前面已经创建的元素名称，禁止引用不存在的元素
4. 严格遵循 FreeCAD 绘图时序：创建基准 → 创建基础几何体 → 布尔运算 → 添加约束 → 导出
5. 绝对不允许合并多个操作到一条命令中
6. 每次最多生成 10 条命令，完成后反馈执行结果再继续
7. 所有命令使用 `--json` 输出格式
8. 多步工作流使用 `--project` 参数保持会话状态

---

## 五阶段执行流

### 阶段 1: 工具选型

**目标**: 从任务需求中识别出需要用到的所有命令组和命令。

**输出格式**:
```
## 阶段 1: 工具选型

### 需要的命令组
| 命令组 | 用途 | 使用次数 |
|--------|------|---------|
| document | 创建和管理文档 | 2 |
| part | 创建 3D 基元和操作 | 5 |
| export | 导出文件 | 2 |

### 需要的具体命令
| 命令 | 用途 |
|------|------|
| document new | 创建新文档 |
| part add box | 创建长方体 |
| part add cylinder | 创建圆柱体 |
| part boolean cut | 布尔差集 |
| export step | 导出 STEP |
| export stl | 导出 STL |
```

**规则**:
- 每个命令必须来自 TOOL_SCHEMA.json 中的定义
- 不需要的命令不要列出
- 标注每个命令的使用次数

---

### 阶段 2: 任务拆解

**目标**: 将整体任务拆分为原子步骤，每个步骤对应一条 CLI 命令。

**输出格式**:
```
## 阶段 2: 任务拆解

| 步骤 | 操作 | 命令 | 依赖 |
|------|------|------|------|
| 1 | 创建文档 | document new --name MyPart | 无 |
| 2 | 创建底板 | part add box --name BasePlate | 步骤 1 |
| 3 | 创建圆柱 | part add cylinder --name Pillar | 步骤 1 |
| 4 | 布尔差集 | part boolean cut --base BasePlate --tool Pillar | 步骤 2, 3 |
| 5 | 导出 STEP | export step --output model.step | 步骤 4 |
| 6 | 导出 STL | export stl --output model.stl | 步骤 4 |
```

**规则**:
- 每个步骤只做一件事
- 步骤编号从 1 开始
- 明确标注每个步骤依赖的前置步骤
- 依赖必须是已完成步骤的编号

---

### 阶段 3: 坐标与依赖计算

**目标**: 对每一步明确写出坐标计算过程、依赖元素和拓扑关系。

**输出格式**:
```
## 阶段 3: 坐标与依赖计算

### 步骤 1: 创建文档
- 坐标计算: 无（文档操作不涉及坐标）
- 依赖元素: 无
- 拓扑关系: 无

### 步骤 2: 创建底板
- 坐标计算: 原点 (0,0,0)，尺寸 100×100×10mm
  - 左下角: (0, 0, 0)
  - 右上角: (100, 100, 10)
- 依赖元素: 步骤 1 创建的文档 "MyPart"
- 拓扑关系: 基础几何体，世界坐标系原点

### 步骤 3: 创建圆柱
- 坐标计算: 圆心在底板上表面中心 (50, 50, 10)，半径 5，高度 20
  - 圆心 X = 100/2 = 50
  - 圆心 Y = 100/2 = 50
  - 圆心 Z = 10（底板上表面）
- 依赖元素: 步骤 1 创建的文档 "MyPart"
- 拓扑关系: 依附在底板 BasePlate 的上表面

### 步骤 4: 布尔差集
- 坐标计算: 无（继承 BasePlate 和 Pillar 的位置）
- 依赖元素: 步骤 2 的 BasePlate，步骤 3 的 Pillar
- 拓扑关系: 用 Pillar 从 BasePlate 中减去，形成通孔
```

**规则**:
- 每个步骤必须有坐标计算过程（无坐标的操作标注"无"）
- 坐标计算必须写出推导过程（如 "X = 100/2 = 50"）
- 明确标注依赖的元素名称（不是步骤编号）
- 标注元素之间的拓扑关系（如"依附在...上表面"）

---

### 阶段 4: 依赖校验

**目标**: 检查所有步骤的依赖关系是否合法。

**输出格式**:
```
## 阶段 4: 依赖校验

| 步骤 | 依赖 | 状态 | 说明 |
|------|------|------|------|
| 1 | 无 | ✅ 合法 | 第一步无依赖 |
| 2 | 步骤 1 | ✅ 合法 | 步骤 1 创建文档，步骤 2 需要文档 |
| 3 | 步骤 1 | ✅ 合法 | 步骤 1 创建文档，步骤 3 需要文档 |
| 4 | 步骤 2, 3 | ✅ 合法 | 步骤 2 创建 BasePlate，步骤 3 创建 Pillar |
| 5 | 步骤 4 | ✅ 合法 | 步骤 4 完成布尔运算后可导出 |
| 6 | 步骤 4 | ✅ 合法 | 步骤 4 完成布尔运算后可导出 |

### 校验结果
- 所有依赖合法 ✅
- 无循环依赖 ✅
- 无悬空引用 ✅
```

**规则**:
- 每个步骤的依赖必须指向已存在的步骤
- 不允许循环依赖（A 依赖 B，B 依赖 A）
- 不允许引用不存在的元素
- 如果有不合法依赖，必须重新调整步骤顺序

---

### 阶段 5: 命令输出

**目标**: 按顺序逐条输出 CLI 命令，每条命令附带注释说明。

**输出格式**:
```
## 阶段 5: 命令输出

# 步骤 1: 创建文档
fc document new --name MyPart --json

# 步骤 2: 创建底板 (100x100x10mm，原点)
fc part add box --name BasePlate --param Length=100 --param Width=100 --param Height=10 --json

# 步骤 3: 创建圆柱 (圆心在底板上表面中心，半径5，高度20)
fc part add cylinder --name Pillar --param Radius=5 --param Height=20 --position 50,50,10 --json

# 步骤 4: 布尔差集 (从底板中减去圆柱，形成通孔)
fc part boolean cut --base BasePlate --tool Pillar --name BasePlate_With_Hole --json

# 步骤 5: 导出 STEP
fc export step --output model.step --overwrite --json

# 步骤 6: 导出 STL
fc export stl --output model.stl --tolerance 0.05 --overwrite --json
```

**规则**:
- 每条命令前用 `#` 注释说明步骤编号和用途
- 命令必须完整可复制执行
- 使用 `--json` 输出格式
- 导出命令使用 `--overwrite` 避免文件存在错误

---

## 完整示例

### 需求
"创建一个 100×100×10 的底板，在底板中心打一个直径 20 的通孔，导出 STEP 和 STL"

### 阶段 1: 工具选型

| 命令组 | 用途 | 使用次数 |
|--------|------|---------|
| document | 创建文档 | 1 |
| part | 创建基元 + 布尔运算 | 3 |
| export | 导出文件 | 2 |

| 命令 | 用途 |
|------|------|
| document new | 创建新文档 |
| part add box | 创建底板 |
| part add cylinder | 创建孔圆柱 |
| part boolean cut | 布尔差集 |
| export step | 导出 STEP |
| export stl | 导出 STL |

### 阶段 2: 任务拆解

| 步骤 | 操作 | 依赖 |
|------|------|------|
| 1 | 创建文档 "BasePlateDoc" | 无 |
| 2 | 创建底板 100×100×10mm | 步骤 1 |
| 3 | 创建圆柱 直径20 高10mm，中心 (50,50,10) | 步骤 1 |
| 4 | 布尔差集：底板 - 圆柱 | 步骤 2, 3 |
| 5 | 导出 STEP | 步骤 4 |
| 6 | 导出 STL | 步骤 4 |

### 阶段 3: 坐标与依赖计算

**步骤 1: 创建文档**
- 坐标: 无
- 依赖: 无
- 拓扑: 无

**步骤 2: 创建底板**
- 坐标: 原点 (0,0,0)，尺寸 100×100×10
  - X: 0 → 100, Y: 0 → 100, Z: 0 → 10
- 依赖: 文档 "BasePlateDoc"
- 拓扑: 世界坐标系原点

**步骤 3: 创建圆柱**
- 坐标: 圆心 (50, 50, 10)，半径 10，高度 10
  - X = 100/2 = 50, Y = 100/2 = 50, Z = 10（底板上表面）
  - 直径 20 → 半径 = 20/2 = 10
- 依赖: 文档 "BasePlateDoc"
- 拓扑: 圆柱底面与底板上表面齐平

**步骤 4: 布尔差集**
- 坐标: 继承底板位置
- 依赖: "BasePlate", "Hole_Cylinder"
- 拓扑: 从底板中减去圆柱形成通孔

**步骤 5-6: 导出**
- 坐标: 无
- 依赖: "BasePlate_With_Hole"
- 拓扑: 无

### 阶段 4: 依赖校验

| 步骤 | 依赖 | 状态 |
|------|------|------|
| 1 | 无 | ✅ |
| 2 | 步骤 1 (文档) | ✅ |
| 3 | 步骤 1 (文档) | ✅ |
| 4 | 步骤 2 (底板), 步骤 3 (圆柱) | ✅ |
| 5 | 步骤 4 (布尔结果) | ✅ |
| 6 | 步骤 4 (布尔结果) | ✅ |

### 阶段 5: 命令输出

```bash
# 步骤 1: 创建文档
fc document new --name BasePlateDoc --json

# 步骤 2: 创建底板 (100x100x10mm)
fc part add box --name BasePlate --param Length=100 --param Width=100 --param Height=10 --json

# 步骤 3: 创建孔圆柱 (直径20，圆心在底板上表面中心)
fc part add cylinder --name Hole_Cylinder --param Radius=10 --param Height=10 --position 50,50,10 --json

# 步骤 4: 布尔差集 (打通孔)
fc part boolean cut --base BasePlate --tool Hole_Cylinder --name BasePlate_With_Hole --json

# 步骤 5: 导出 STEP
fc export step --output base_plate.step --overwrite --json

# 步骤 6: 导出 STL
fc export stl --output base_plate.stl --tolerance 0.05 --overwrite --json
```

---

## 预期输出

```
> fc document new --name BasePlateDoc --json
{"status":"ok","operation":"document_new","data":{"name":"BasePlateDoc"}}

> fc part add box --name BasePlate --param Length=100 --param Width=100 --param Height=10 --json
{"status":"ok","operation":"part_add","data":{"name":"BasePlate","type_id":"Part::Box"}}

> fc part add cylinder --name Hole_Cylinder --param Radius=10 --param Height=10 --position 50,50,10 --json
{"status":"ok","operation":"part_add","data":{"name":"Hole_Cylinder","type_id":"Part::Cylinder"}}

> fc part boolean cut --base BasePlate --tool Hole_Cylinder --name BasePlate_With_Hole --json
{"status":"ok","operation":"part_boolean","data":{"name":"BasePlate_With_Hole"}}

> fc export step --output base_plate.step --overwrite --json
{"status":"ok","operation":"export_step","data":{"file":"base_plate.step"}}

> fc export stl --output base_plate.stl --tolerance 0.05 --overwrite --json
{"status":"ok","operation":"export_stl","data":{"file":"base_plate.stl"}}
```

---

## 常见错误和禁止规则

### 禁止规则
- ❌ 禁止在 Z=0 以下创建几何体（默认工作平面 Z=0）
- ❌ 禁止用不存在的元素作为布尔运算的目标
- ❌ 禁止在没有依附平面的情况下创建圆形
- ❌ 禁止一次性生成超过 10 条命令
- ❌ 禁止跳过任何阶段

### 常见错误
1. **坐标计算错误**: 相对坐标没有正确计算参照元素的位置
2. **依赖顺序错误**: 后续命令引用了尚未创建的元素
3. **参数单位错误**: 所有尺寸默认是 mm，不要混淆
4. **名称冲突**: 同一文档中元素名称必须唯一
5. **缺少 --json**: 所有命令必须使用 `--json` 输出

### 错误恢复
当命令执行失败时：
1. 读取错误信息中的 `error.code` 和 `error.suggestion`
2. 根据错误类型调整命令（见 TOOL_SCHEMA.json 中的 error_codes）
3. 重新输出修正后的命令
4. 如果连续失败 3 次，暂停并请求人工介入

---

## 与 Planner 的集成

Planner 生成的 Plan 对象包含五阶段所需的所有信息：
- **阶段 1**: 从 Plan.tasks 中的 task.type 字段提取命令组
- **阶段 2**: Plan.tasks 列表本身就是任务拆解
- **阶段 3**: Task.params 包含坐标和依赖信息
- **阶段 4**: Task.dependencies 定义依赖关系
- **阶段 5**: Task.args 是可直接执行的命令参数

AI Agent 在生成 Plan 后，应按照此模板格式输出五阶段信息，
让人类或其他 AI 可以验证和复现整个建模过程。
