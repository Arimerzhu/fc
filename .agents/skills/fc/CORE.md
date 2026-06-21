---
name: fc-core
description: fc 核心技能 — 五阶段执行流、全局规则、错误处理。每次任务必读。
---

# fc-core — fc 核心执行技能

## 什么是 fc

fc 是 Agent Native FreeCAD CLI — 面向 AI Agent 的命令行工具，支持 258+ 命令，覆盖 FreeCAD 全部工作台。

## 全局选项

所有命令均支持以下全局选项，必须在子命令**之前**指定：

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--json` | JSON 格式输出（AI Agent 必选） | `false` |
| `--backend` | 后端类型：`headless`（FreeCADCmd）或 `rpc`（FreeCAD GUI） | `headless` |
| `--freecad-path` | FreeCAD 可执行文件路径（覆盖自动检测） | 自动检测 |
| `--project` / `-p` | 项目文件路径（会话持久化：历史/快照） | 无 |
| `--host` | RPC 主机地址 | `localhost` |
| `--port` | RPC 端口 | `9875` |
| `--session` | 会话 ID（RPCBackend 绑定），自动生成 | `--backend` 决定 |

**示例：**
```bash
fc --json --project mypart.FCStd document new --name MyPart
```

---

## 五阶段执行流（强制）

> **跳过任何阶段 = 任务失败。** 必须按顺序执行全部五个阶段。

### Phase 1：工具选择

列出任务所需的全部命令组和命令。从以下命令组中选择：

| 命令组 | 用途 |
|--------|------|
| `document` | 文档管理（new/open/save/info/close/list）|
| `session` | 会话管理（undo/redo/status/history/snapshot/restore）|
| `part` | 3D 基元与布尔操作 |
| `sketch` | 2D 草图 |
| `body` | PartDesign 实体 |
| `export` | 导出（step/stl/obj/brep/dxf/svg/pdf/gltf/3mf/fcstd）|
| `import` | 导入 |
| `mesh` | 网格操作 |
| `draft` | 草图工作台 |
| `surface` | 曲面操作 |
| `techdraw` | 工程图 |
| `assembly` | 装配 |
| `fem` | 有限元分析 |
| `cam` | 数控加工 |
| `spreadsheet` | 电子表格 |
| `material` | 材质 |
| `execute` | 执行 Python 代码/宏文件 |
| `agent` | 自主 CAD 设计：自然语言 → 计划 → 执行 → BOM |
| `repl` | 交互式 REPL 模式（持久会话） |

详细命令参考见对应 `docs/skills/fc-*/SKILL.md`。

### Phase 2：任务分解

将任务拆解为原子步骤，每步对应一条 CLI 命令。

- 每个步骤只做**一件事**
- 步骤间有明确的**输入输出关系**
- 命名规范：`{Type}_{Seq}`（如 `Box_01`、`Cyl_02`、`Hole_03`）

### Phase 3：坐标与依赖

- 计算所有几何体的**坐标和尺寸**
- 确定**依赖关系**：哪些元素必须先创建
- 确定**拓扑关系**：布尔操作的 base 和 tool 分别是谁
- 绘制依赖图（如有必要）

### Phase 4：依赖验证（DFS）

对依赖图执行深度优先搜索验证：

- **无悬空引用**：每个被引用的元素必须已创建
- **无循环依赖**：A 依赖 B，B 不能依赖 A
- **顺序正确**：被依赖的元素在依赖它的元素之前

### Phase 5：命令输出

按依赖顺序输出 CLI 命令，每条命令附带注释说明。

---

## 核心规则

### ✅ 必须做

| 规则 | 说明 |
|------|------|
| 始终使用 `--json` | AI Agent 需要结构化输出 |
| 唯一命名 `{Type}_{Seq}` | 避免名称冲突，如 `Box_01`、`Cyl_02` |
| 只引用已创建的元素 | 引用前必须确认元素存在 |
| 多步骤使用 `--project` | 启用会话持久化和快照 |
| 每批最多 10 条命令 | 避免超时和上下文溢出 |
| 先创建文档 | 任何几何操作前必须先 `document new` |

### ❌ 禁止做

| 规则 | 说明 |
|------|------|
| 编造不存在的命令 | 只使用本文档和 SKILL.md 中的命令 |
| 合并多个操作为一条命令 | 每步一条命令 |
| 跳过执行阶段 | 五阶段必须完整执行 |
| 引用尚未创建的元素 | 会导致 NOT_FOUND 错误 |
| 几何体低于 Z=0 | 默认工作平面为 Z=0 |

---

## 错误处理

### 错误 JSON 格式

```json
{
  "status": "error",
  "message": "详细错误信息",
  "code": "ERROR_CODE",
  "suggestion": "修复建议"
}
```

### 常见错误码

| 错误码 | 含义 | 恢复策略 |
|--------|------|----------|
| `NOT_FOUND` | 引用的对象不存在 | 检查名称拼写；确认对象已创建 |
| `CREATE_FAILED` | 对象创建失败 | 检查参数合法性；确认文档已打开 |
| `FILE_EXISTS` | 文件已存在 | 添加 `--overwrite` 标志 |
| `BOOLEAN_FAILED` | 布尔操作失败 | 确认 base 和 tool 存在且有交集 |
| `TIMEOUT` | 执行超时 | 减少批量命令数量；检查几何复杂度 |
| `INVALID_NAME` | 非法名称 | 使用字母、数字、下划线、连字符 |
| `INVALID_TYPE` | 非法类型 | 使用有效类型：`box/cylinder/sphere/cone/torus/wedge/helix/ellipsoid/spiral` |

---

## 自动学习（ErrorRulesEngine）

fc 运行时内置错误规则引擎，自动从失败中学习：

1. **记录错误**：每次命令失败，提取错误模式（类型 + 上下文）
2. **计数累加**：相同模式出现 **>= 3 次** 时，自动生成**禁止规则**
3. **规则注入**：活动规则自动注入规划提示，防止重复犯错
4. **持久化**：规则可导出/导入 JSON 文件，跨会话保留

```bash
# 查看当前会话的错误规则摘要
fc --json session status
```

---

## 意图 → 命令速查表

| 意图 | 命令 |
|------|------|
| 新建项目 | `fc document new --name Name` |
| 打开文件 | `fc document open path.FCStd` |
| 创建立方体 | `fc part add box --name Box_01 -P Length=20 -P Width=15 -P Height=10` |
| 创建圆柱 | `fc part add cylinder --name Cyl_01 -P Radius=5 -P Height=20` |
| 创建球体 | `fc part add sphere --name Sphere_01 -P Radius=10` |
| 布尔求和 | `fc part boolean fuse Base Tool --name Result` |
| 布尔求差 | `fc part boolean cut Base Tool --name Result` |
| 布尔求交 | `fc part boolean common Base Tool --name Result` |
| 3D 圆角 | `fc part fillet-3d Name --radius 2 --edges all` |
| 3D 倒角 | `fc part chamfer-3d Name --distance 1 --edges 0,1` |
| 打孔 | `fc part hole Name --diameter 8 --depth 10` |
| 导出 STEP | `fc export step --output model.step --overwrite` |
| 导出 STL | `fc export stl --output model.stl --overwrite` |
| 撤销 | `fc session undo` |
| 重做 | `fc session redo` |
| 创建快照 | `fc session snapshot v1 --description "初始版本"` |
| 恢复快照 | `fc session restore v1` |
| 执行代码 | `fc execute code "print(FreeCAD.ActiveDocument.Name)"` |
| 执行宏文件 | `fc execute file macro.py` |
| 变换位置 | `fc part transform Name --position 10,20,30` |
