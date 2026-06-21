# AI Agent 使用 fc 完整指南

> 本文档面向 AI Agent。读完即可独立使用 fc 完成 CAD 建模任务。

## 第一步：了解工具集

读取以下文件，建立工具认知：

1. **`docs/skills/SKILL.md`** — Skill 索引，了解加载策略
2. **`docs/skills/CORE.md`** — 核心技能：五阶段执行流 + 全局规则（必读）
3. **`docs/skills/FUNDAMENTALS.md`** — 基础技能：document/session/execute（必读）
4. **按任务类型加载对应 skill**：
   - 创建几何体 → `docs/skills/MODELING.md`
   - 装配/分析 → `docs/skills/ENGINEERING.md`
   - 出图/标注 → `docs/skills/DRAFTING.md`
   - 导入导出 → `docs/skills/DATA_EXCHANGE.md`
5. **`docs/TOOL_SCHEMA.json`** — 185 个命令的机器可读 schema
6. **`docs/FUNCTION_SCHEMAS.json`** — 函数调用定义（如果用 function calling）
7. **`docs/examples/`** — 5 个验证过的示例（模仿风格）

## 第二步：五阶段执行流（必须遵守）

每次设计任务必须按以下 5 个阶段执行。**跳过任何一步都算失败。**

### Phase 1: 工具选型

从 TOOL_SCHEMA.json 中选出需要的命令组和命令。

输出格式：
```
## Phase 1: Tool Selection

### Command Groups
| Group | Usage Count |
|-------|-------------|
| document | 1 |
| part | 3 |
| export | 1 |

### Commands
| Command | Purpose |
|---------|---------|
| document new | Create new document |
| part add | Create primitive |
| part boolean | Boolean operation |
| export step | Export to STEP |
```

### Phase 2: 任务拆解

将任务拆为原子步骤，每步一条 CLI 命令。

输出格式：
```
## Phase 2: Task Decomposition

| Step | Operation | Command | Dependencies |
|------|-----------|---------|--------------|
| 1 | Create document | `fc document new` | None |
| 2 | Add base box | `fc part add box` | task_001 |
| 3 | Add cylinder | `fc part add cylinder` | task_001 |
| 4 | Boolean cut | `fc part boolean cut` | task_002, task_003 |
| 5 | Export STEP | `fc export step` | task_004 |
```

### Phase 3: 坐标与依赖计算

对每个步骤：计算坐标、标注依赖元素、描述拓扑关系。

输出格式：
```
## Phase 3: Coordinate & Dependency Calculation

### Step 1: Create document
- **Coordinates**: N/A (document operation)
- **Dependency Elements**: None
- **Topology**: N/A

### Step 2: Add base box
- **Coordinates**: Length=100, Width=50, Height=20
- **Dependency Elements**: [MyPart (document)]
- **Topology**: Base geometry at world origin

### Step 3: Add cylinder (hole)
- **Coordinates**: Radius=5, Height=20, position=50,25,0 (center of box top face)
- **Dependency Elements**: [MyPart (document)]
- **Topology**: Cylinder centered on box top face, Z=0 plane
```

### Phase 4: 依赖校验

检查所有依赖合法，无悬空引用，无循环依赖。

输出格式：
```
## Phase 4: Dependency Validation

| Step | Dependencies | Status | Notes |
|------|-------------|--------|-------|
| 1 | None | ✅ PASS | First step |
| 2 | task_001 | ✅ PASS | task_001 = Create document |
| 3 | task_001 | ✅ PASS | task_001 = Create document |
| 4 | task_002, task_003 | ✅ PASS | Both exist |
| 5 | task_004 | ✅ PASS | task_004 = Boolean cut |

### Circular Dependency Check
- ✅ No circular dependencies detected

**Result**: ALL VALID
```

### Phase 5: 命令输出

按顺序输出 CLI 命令，每条带注释。

输出格式：
```
## Phase 5: Command Output

```bash
# Step 1: Create new FreeCAD document
fc document new --name MyPart --json

# Step 2: Add base box 100x50x20mm
fc part add box --name Box_001 --param Length=100 --param Width=50 --param Height=20 --json

# Step 3: Add cylinder hole (centered on top face)
fc part add cylinder --name Cyl_001 --param Radius=5 --param Height=20 --json

# Step 4: Boolean cut (subtract cylinder from box)
fc part boolean cut --base Box_001 --tool Cyl_001 --name Result_001 --json

# Step 5: Export to STEP
fc export step --output model.step --overwrite --json
```
```

## 第三步：执行命令

### 基本执行

```bash
# 单条命令
fc part add box --name Box --param Length=10 --json

# 多步工作流（使用 --project 保持会话）
fc --project model.FCStd document new --name MyPart --json
fc --project model.FCStd part add box --name Box --param Length=10 --json
fc --project model.FCStd document save --json
```

### 批量执行（推荐）

```bash
# 使用 execute 命令执行多步脚本
fc execute code "
import FreeCAD
doc = FreeCAD.newDocument('MyPart')
box = doc.addObject('Part::Box', 'Box')
box.Length = 100
box.Width = 50
box.Height = 20
doc.recompute()
" --json
```

### AI Agent 模式

```bash
# 自然语言 → CAD（Planner 自动生成五阶段计划并执行）
fc agent "创建一个 100x50x20mm 的底板，中心有直径 10mm 的通孔，导出 STEP"

# 指定项目文件
fc agent --project model.FCStd "创建一个盒子"
```

## 第四步：错误处理

### 错误响应格式

```json
{
  "status": "error",
  "operation": "part_add",
  "error": {
    "code": "CREATE_FAILED",
    "message": "Object creation failed: invalid parameters",
    "suggestion": "Check parameters, ensure document is open"
  }
}
```

### 常见错误及恢复

| 错误码 | 原因 | 恢复策略 |
|--------|------|----------|
| `NOT_FOUND` | 对象不存在 | 检查名称拼写，确认已创建 |
| `CREATE_FAILED` | 创建失败 | 检查参数，确认文档已打开 |
| `FILE_EXISTS` | 文件已存在 | 添加 `--overwrite` |
| `NO_DOCUMENT` | 无活动文档 | 先执行 `fc document new` |
| `BOOLEAN_FAILED` | 布尔运算失败 | 确认两个对象都存在且有有效形状 |
| `TIMEOUT` | 超时 | 增加 `--timeout` 或简化操作 |

### 自动错误学习

fc 会自动记录错误模式。同一错误 ≥3 次后，会自动生成禁止规则并存入 `docs/ERROR_RULES.md`。

## 核心规则速查

### 必须做 ✅

1. **始终使用 `--json`** — 结构化输出，AI 可解析
2. **唯一命名** — `{类型}_{序号}` 格式（Box_001, Cyl_001）
3. **只引用已创建的元素** — 不能引用未来步骤的元素
4. **使用 `--project`** — 多步工作流保持会话状态
5. **分批执行** — 每批 ≤10 命令，执行完反馈结果
6. **先创建文档** — 任何建模前先 `fc document new`

### 禁止做 ❌

1. **不编造命令** — 只用 TOOL_SCHEMA.json 中的命令
2. **不合并操作** — 一条命令只做一件事
3. **不跳过阶段** — 五阶段必须完整
4. **不引用未创建元素** — 依赖必须指向已完成的步骤
5. **不在 Z=0 以下建模** — 默认工作平面约束

## 快速参考

### 意图→命令映射

| 用户意图 | 命令 |
|----------|------|
| 创建盒子 | `fc part add box --name Box --param Length=20 --param Width=15 --param Height=10 --json` |
| 创建圆柱 | `fc part add cylinder --name Cyl --param Radius=5 --param Height=20 --json` |
| 布尔并集 | `fc part boolean fuse --base Box --tool Cyl --name Fused --json` |
| 布尔切割 | `fc part boolean cut --base Box --tool Cyl --name Cut --json` |
| 布尔交集 | `fc part boolean common --base Box --tool Cyl --name Common --json` |
| 导出 STEP | `fc export step --output model.step --overwrite --json` |
| 导出 STL | `fc export stl --output model.stl --tolerance 0.05 --overwrite --json` |
| 保存项目 | `fc document save --output project.FCStd --overwrite --json` |
| 撤销 | `fc session undo --json` |
| 创建快照 | `fc session snapshot v1 --description "初始设计" --json` |
| 创建草图 | `fc sketch new --name MySketch --plane XY --json` |
| 添加圆 | `fc sketch add-circle MySketch --center 0,0 --radius 10 --json` |
| 拉伸 | `fc body pad Body001 Sketch001 --length 20 --json` |
| 倒角 | `fc part fillet-3d Box --radius 2 --json` |
| 倒直角 | `fc part chamfer-3d Box --size 1.5 --json` |
| 镜像 | `fc part mirror Box --plane XY --name BoxMirrored --json` |
| 缩放 | `fc part scale Box 1.5 --json` |
| 创建孔 | `fc part hole Box --diameter 8 --depth 10 --json` |
| 创建工程图 | `fc techdraw page --name Page1 --format A3 --json` |
| 添加视图 | `fc techdraw view --page Page1 --source Box --direction 0,0,1 --scale 1.0 --json` |
| 创建电子表格 | `fc spreadsheet create --name Params --json` |
| 设置参数 | `fc spreadsheet set --sheet Params --cell A1 --value 100 --json` |
| 分配材料 | `fc material assign --object Box --material Steel --json` |
| 导入 STEP | `fc import step model.step --json` |
| 执行 Python | `fc execute code "print(FreeCAD.ActiveDocument.Name)" --json` |

## 学习路径

1. **先读示例** — `docs/examples/01_simple_box_with_hole.md`（最简单）
2. **模仿风格** — 按五阶段格式输出
3. **逐步复杂** — 从简单示例到复杂工作流
4. **查阅 schema** — 遇到不确定的参数查 TOOL_SCHEMA.json
