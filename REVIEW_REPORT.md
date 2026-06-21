# fc 项目全量架构审查报告

审查范围：全量（packages/core, packages/cli, packages/mcp, packages/runtime）
审查时间：2026-06-10
总体评级：⚠️ 需修改

---

## 审查 1：架构分层合规性

### 1.1 CLI 层 `import FreeCAD` 分析

**发现**：CLI 层所有 `import FreeCAD` 语句均出现在传递给 `backend.execute_code()` 的代码字符串中，而非 CLI 进程本身直接调用 FreeCAD API。

**结论**：CLI 层未直接 import FreeCAD 模块。所有 FreeCAD 操作均通过 `_get_backend()` 获取后端实例，再调用后端方法或 `backend.execute_code()` 执行。**合规**。

### 1.2 CLI 层 `from fc_core` 导入分析

**发现**：CLI 命令文件仅从 `fc_core` 导入以下内容：
- `from fc_core.backend import RPCBackend / HeadlessBackend`（在 `_get_backend()` 内部）
- `from fc_core.types import Vec3`（仅在 `part.py` 中用于参数解析）

**结论**：CLI 层未直接导入 FreeCAD 能力层（geometry、io 等），仅导入 backend 和 types。**合规**。

### 1.3 `_get_backend()` 使用检查

**发现**：所有 16 个 CLI 命令文件均定义了 `_get_backend()` 函数，且每个命令函数内部均通过 `backend = _get_backend()` 获取后端实例。

**结论**：**合规**。

### 1.4 MCP 层 `import FreeCAD` 分析

**发现**：MCP 工具层存在直接 `import FreeCAD` 语句，出现在以下位置：
- `packages/mcp/src/fc_mcp/tools/export.py:52,152` -- 在传递给 `be.execute_code()` 的代码字符串中
- `packages/mcp/src/fc_mcp/tools/sketch.py:65,101,139,186,228,269,301,333,369,403,430` -- 同上
- `packages/mcp/src/fc_mcp/tools/query.py:63,96,135` -- 同上
- `packages/mcp/src/fc_mcp/tools/geometry.py:412` -- 同上

**分析**：与 CLI 层相同，这些 `import FreeCAD` 均出现在传递给 `be.execute_code()` 的代码字符串中，在 FreeCAD 子进程内执行，不在 MCP 服务器进程内执行。

**结论**：从进程隔离角度看，**技术上合规**。但代码字符串中硬编码 `import FreeCAD` 存在维护风险（见"接口问题"部分）。

---

## 审查 2：ToolResponse 格式一致性

### 2.1 直接返回 dict 的情况

**发现**：以下位置直接返回 `dict` 而非 `ToolResponse`：

| 文件 | 行号 | 场景 |
|------|------|------|
| `packages/core/src/fc_core/backend/__init__.py` | 340-341 | `_execute_macro()` 返回原始 dict（内部方法，被外层包装为 ToolResponse） |
| `packages/core/src/fc_core/backend/__init__.py` | 911 | RPC `_call()` 返回原始 dict（内部方法） |
| `packages/core/src/fc_core/io/import_mod.py` | 206 | `list_supported_formats()` 返回 dict（非操作函数，仅查询） |
| `packages/core/src/fc_core/io/export.py` | 69 | `list_presets()` 返回 dict（非操作函数，仅查询） |
| `packages/mcp/src/fc_mcp/tools/export.py` | 63-65 | `export_stl()` 成功时直接构造 dict |
| `packages/mcp/src/fc_mcp/tools/export.py` | 172-173 | `export_pdf()` 成功时直接构造 dict |
| `packages/mcp/src/fc_mcp/tools/query.py` | 178 | `get_version()` 直接构造 dict |
| `packages/runtime/src/fc_runtime/bom.py` | 35,61 | `BOMItem.to_dict()` / `BOM.to_dict()` 返回 dict（数据类方法） |
| `packages/runtime/src/fc_runtime/planner.py` | 74,98 | 返回 dict（内部数据结构） |

**问题详情**：

1. **`export_stl()` (export.py:63-65)** 和 **`export_pdf()` (export.py:172-173)**：成功时直接构造 `{"status": "ok", ...}` dict，而非使用 `ToolResponse.ok()`。这导致返回格式缺少 `operation` 字段和 `error` 字段结构，与 ToolResponse 标准格式不一致。

2. **`get_version()` (query.py:178)**：直接构造 dict，缺少 `operation` 字段。

**严重程度**：中。这些函数返回值通过 `r.to_dict()` 或作为 dict 直接返回给 MCP 调用方。虽然功能正常，但格式不统一可能导致 AI agent 解析失败。

### 2.2 ToolResponse.ok/error 使用

**发现**：`fc_core/backend/__init__.py` 中所有公开方法均正确使用 `ToolResponse.ok()` 和 `ToolResponse.error()` 返回。

**结论**：**核心层合规**。

---

## 审查 3：MCP 工具规范

### 3.1 `@mcp.tool()` 装饰器

**发现**：共 50 个 `@mcp.tool()` 装饰器，分布在 6 个模块：
- document.py: 6 个
- export.py: 10 个
- geometry.py: 14 个
- execute.py: 2 个
- query.py: 6 个
- sketch.py: 12 个

**结论**：**合规**。

### 3.2 `backend: str = "headless"` 参数

**发现**：所有 50 个 MCP 工具函数均包含 `backend: str = "headless"` 参数。

**结论**：**合规**。

### 3.3 Docstring 完整性

**发现**：所有 50 个 MCP 工具函数均包含 docstring，且大部分有 `Args:` 部分。

**结论**：**合规**。

### 3.4 返回格式

**发现**：47/50 个工具通过 `r.to_dict()` 返回 ToolResponse 的标准 dict 格式。3 个工具（`export_stl`, `export_pdf`, `get_version`）直接构造 dict。

**结论**：**基本合规，3 处需修正**。

---

## 审查 4：安全审查

### 4.1 subprocess 调用 timeout

**发现**：所有 `subprocess.run()` 调用均包含 `timeout` 参数：

| 文件 | 行号 | timeout 值 |
|------|------|------------|
| `packages/core/src/fc_core/backend/__init__.py` | 282 | `timeout or self._timeout`（默认 120s） |
| `packages/runtime/src/fc_runtime/executor.py` | 153 | `self._timeout`（默认 120s） |
| `packages/runtime/src/fc_runtime/executor.py` | 271 | `self._timeout`（默认 120s） |
| `packages/runtime/src/fc_runtime/bom.py` | 253 | `self._timeout`（默认 120s） |

**结论**：**合规**。

### 4.2 路径验证

**发现**：
- 文件路径操作普遍使用 `os.path.abspath()` 进行规范化
- `import_cmd.py:38-39` 使用 `os.path.isfile()` 验证文件存在
- `execute.py:50-51` 使用 `os.path.isfile()` 验证文件存在
- 导出命令普遍检查 `os.path.exists()` 防止覆盖

**缺失**：
- 无路径遍历防护（如 `..` 检查）。用户可传入 `../../etc/passwd` 等路径，`os.path.abspath()` 会将其解析为绝对路径但不阻止写入。
- 无输出目录白名单。

**严重程度**：中。CLI 工具通常由受信任用户使用，但作为 AI agent 工具链，路径遍历风险需要关注。

### 4.3 execute_code 安全风险

**发现**：
- `execute_code` 和 `execute_file` 命令允许执行任意 Python 代码
- CLI 层 `execute.py` 有 docstring 警告："Execute arbitrary Python code in FreeCAD"
- MCP 层 `execute.py` 有 docstring 说明
- 无代码内容审查或沙箱限制
- 无执行权限控制

**严重程度**：高（设计如此，但需明确文档化）。这是 `execute` 命令的固有设计，应在使用文档中明确警告。

### 4.4 RPC 仅 localhost

**发现**：`RPCBackend` 默认 `host="localhost"`，CLI 默认 `--host localhost`。

**结论**：**合规**。

### 4.5 快照名称验证

**发现**：`snapshot` 命令（session_cmd.py:226）直接使用用户输入的 `name` 参数构造文件路径 `os.path.join(hist_dir, "snapshots", name)`，无白名单验证。

**风险**：用户可传入 `../../etc/snapshot_name` 等路径遍历字符串，导致快照文件写入任意目录。

**严重程度**：高。

### 4.6 硬编码密钥/Token

**发现**：无硬编码密钥或 token。

**结论**：**合规**。

---

## 审查 5：性能审查

### 5.1 子进程开销

**发现**：HeadlessBackend 每个操作均启动新的 FreeCADCmd 进程（~1-3s 开销）。这是已知限制（ARCHITECTURE.md 第 10 节）。

**结论**：已知限制，已在 ADR-011 中记录。

### 5.2 超时配置

**发现**：所有子进程调用均有超时（默认 120s），RPC 后端默认 150s。

**结论**：**合规**。

---

## 审查 6：文档质量

### 6.1 模块 Docstring

**发现**：所有 Python 模块均有 module docstring。

**结论**：**合规**。

### 6.2 ARCHITECTURE.md 一致性

**发现**：ARCHITECTURE.md 描述的架构与实际代码一致。16 个 CLI 命令组、6 个 MCP 工具模块、双后端架构均与代码匹配。

**结论**：**合规**。

---

## 问题汇总

### 架构违规（0 项）

无。

### 接口问题（3 项）

1. **[export.py:63-65]** `export_stl()` 成功时直接构造 dict，缺少 `operation` 字段 → 应使用 `ToolResponse.ok("export", {...}, ...).to_dict()`
2. **[export.py:172-173]** `export_pdf()` 成功时直接构造 dict，缺少 `operation` 字段 → 同上
3. **[query.py:178]** `get_version()` 直接构造 dict，缺少 `operation` 字段 → 应使用 `ToolResponse.ok("get_version", {"version": version}, ...).to_dict()`

### 安全问题（2 项）

1. **[session_cmd.py:226]** 快照名称未做白名单验证，存在路径遍历风险 → 应添加 `re.match(r'^[a-zA-Z0-9_-]+$', name)` 验证
2. **[全量]** 文件路径操作无路径遍历防护 → 建议在 `os.path.abspath()` 后检查解析路径是否在预期目录内

### 性能问题（0 项）

无新发现。已知限制已记录。

### 文档问题（1 项）

1. **[execute.py]** `execute_code` / `execute_file` 命令的安全警告仅在 docstring 中，无显式用户确认机制 → 建议在 CLI 帮助文本中添加 `WARNING: This command executes arbitrary code.`

---

## 修复优先级

| 优先级 | 问题 | 文件 |
|--------|------|------|
| P0 (立即修复) | 快照名称路径遍历 | session_cmd.py:226 |
| P1 (本周修复) | ToolResponse 格式不一致 (3处) | export.py, query.py |
| P2 (后续改进) | 文件路径遍历防护 | 全量 |
| P3 (文档改进) | execute 命令安全警告 | execute.py |

---

## 总结

fc 项目整体架构合规，5 层分层清晰，CLI 和 MCP 层均通过 BackendInterface 访问 FreeCAD，无直接绕过。主要问题集中在：(1) 3 处 MCP 工具直接构造 dict 而非使用 ToolResponse，(2) 快照名称缺少白名单验证存在路径遍历风险，(3) 文件路径操作缺少遍历防护。建议优先修复 P0 安全问题。
