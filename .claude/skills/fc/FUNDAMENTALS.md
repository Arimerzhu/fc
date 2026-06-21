---
name: fc-fundamentals
description: fc 基础技能 — document/session/execute 命令组。每次任务必读。
---

# fc-fundamentals — fc 基础命令技能

每次任务都需要这三个命令组：**document**（文档管理）、**session**（会话管理）、**execute**（代码执行）。

---

## 1. document — 文档管理（6 条命令）

| 命令 | 说明 | 关键参数 | 示例 |
|------|------|----------|------|
| `document new` | 创建新文档 | `--name` 名称, `--output` 保存路径 | `fc document new --name MyPart` |
| `document open` | 打开已有文档 | `path` .FCStd 文件路径 | `fc document open part.FCStd` |
| `document save` | 保存文档 | `--output` 另存为路径 | `fc document save --output backup.FCStd` |
| `document inject-gui` | 注入 GUI 视图数据（仅 RPC）| `--output` 文件路径, `--view` 视角 (isometric/front/top/side/...), `--fit-all` | `fc --session gui document inject-gui -o model.FCStd -v isometric` |
| `document info` | 查看文档信息 | — | `fc --json document info` |
| `document close` | 关闭当前文档 | — | `fc document close` |
| `document list` | 列出打开的文档（仅 RPC）| — | `fc document list` |

### 典型工作流

```bash
# 1. 创建新文档
fc --json document new --name MyPart

# 2. 执行建模操作（part/sketch/body 等）
fc --json part add box --name Box_01 -P Length=20 -P Width=15 -P Height=10

# 3. 保存
fc --json document save --output mypart.FCStd

# 4. 修复 GUI 视图空白（需要先启动 GUI 会话）
fc session start --name gui --mode gui
fc --session gui document open mypart.FCStd
fc --session gui document inject-gui --output mypart.FCStd --view isometric
```

### 常见错误

- **CREATE_FAILED**：FreeCAD 后端未启动或 `--freecad-path` 不正确
- **FILE_EXISTS**：保存路径已存在，需先删除或使用新路径
- **GUI_REQUIRED**：`document inject-gui` 必须在 RPC/GUI 会话模式下调用
- 忘记先 `document new` 就执行几何操作

### ⚠️ FCStd 文件 GUI 视图问题

FreeCADCmd 模式保存的 FCStd 文件不包含 `GuiDocument.xml`、相机位置、ViewProvider 设置，
在 FreeCAD GUI 中打开时 3D 视图是空白的。**解决方法**：

```bash
# 启动 GUI 会话
fc session start --name gui --mode gui

# 打开文件并注入 GUI 数据
fc --session gui document open mypart.FCStd
fc --session gui document inject-gui --output mypart.FCStd
```

---

## 2. session — 会话管理（9 条命令）

| 命令 | 说明 | 关键参数 | 示例 |
|------|------|----------|------|
| `session undo` | 撤销 | `--steps` 步数 | `fc session undo --steps 2` |
| `session redo` | 重做 | `--steps` 步数 | `fc session redo` |
| `session status` | 会话状态 | — | `fc --json session status` |
| `session history` | 操作历史 | `--limit` 条数 | `fc --json session history --limit 10` |
| `session snapshot` | 创建快照 | `name` 名称, `--description` 描述 | `fc session snapshot v1 -d "初始版本"` |
| `session restore` | 恢复快照 | `name` 名称 | `fc session restore v1` |
| `session list` | 列出快照 | — | `fc --json session list` |
| `session start` | 启动 RPC 后端 | — | `fc session start` |
| `session stop` | 停止 RPC 后端 | — | `fc session stop` |

### 典型工作流

```bash
# 创建项目并操作
fc --json --project mypart.FCStd document new --name MyPart
fc --json --project mypart.FCStd part add box --name Box_01 -P Length=20 -P Width=15 -P Height=10

# 创建快照
fc --json --project mypart.FCStd session snapshot v1 -d "基础立方体"

# 继续操作
fc --json --project mypart.FCStd part add cylinder --name Cyl_01 -P Radius=5 -P Height=20

# 查看历史
fc --json --project mypart.FCStd session history

# 撤销
fc --json --project mypart.FCStd session undo

# 恢复到快照
fc --json --project mypart.FCStd session restore v1
```

### 常见错误

- **NO_PROJECT**：未使用 `--project` 导致快照/历史不可用
- **NOT_FOUND**：快照名称不存在
- **INVALID_NAME**：快照名称包含非法字符（只允许 `A-Za-z0-9_-`）

---

## 3. execute — 代码执行（2 条命令）

| 命令 | 说明 | 关键参数 | 示例 |
|------|------|----------|------|
| `execute code` | 执行 Python 代码 | `code` 代码字符串, `--timeout` 超时(秒) | `fc execute code "print('hello')"` |
| `execute file` | 执行 Python 宏文件 | `path` 文件路径, `--timeout` 超时(秒) | `fc execute file macro.py` |

### 典型工作流

```bash
# 执行单行代码
fc --json execute code "doc = FreeCAD.ActiveDocument; print(doc.Name)"

# 执行多行代码（使用换行符）
fc --json execute code "import FreeCAD; doc = FreeCAD.ActiveDocument; print(len(doc.Objects))"

# 执行宏文件
fc --json execute file ./scripts/my_macro.py --timeout 60
```

### 常见错误

- **TIMEOUT**：代码执行超时，增加 `--timeout` 参数
- **FILE_NOT_FOUND**：宏文件路径不存在
- 代码中引用了不存在的对象

---

## 会话持久化（--project）

`--project` 参数是会话持久化的核心。指定后：

| 功能 | 无 `--project` | 有 `--project` |
|------|---------------|----------------|
| 操作历史 | 不记录 | 记录到 `{project}_history/history.json` |
| 快照功能 | 不可用 | 保存到 `{project}_history/snapshots/` |
| 撤销/重做 | 仅当前会话 | 跨命令持久化 |
| 适用场景 | 一次性操作 | 多步骤建模任务 |

**最佳实践：** 所有多步骤建模任务都应使用 `--project`：

```bash
fc --json --project mypart.FCStd document new --name MyPart
# 后续所有命令都带 --project mypart.FCStd
```
