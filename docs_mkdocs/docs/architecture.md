# 架构设计

## 五层架构

```
CLI Layer              ← Click commands, 17 command groups, 185+ commands
  ↓
Agent Runtime Layer    ← Planning, execution, self-correction, BOM
  ↓
Tool Registry Layer    ← MCP tools (6 tool modules, ~50 tools)
  ↓
FreeCAD Capability Layer ← fc-core: backend, geometry, engineering, io
  ↓
FreeCAD Kernel         ← FreeCADCmd / FreeCAD GUI
```

## 双后端

所有 FreeCAD 操作通过 `BackendInterface` 抽象基类：

| 后端 | 类 | 用途 |
|------|-----|------|
| Headless | `HeadlessBackend` | CI/CD, 批处理, 无 GUI |
| RPC | `RPCBackend` | 交互式, 截图, 实时 |

## Monorepo 结构

| 包 | 路径 | 用途 |
|----|------|------|
| `fc-core` | `packages/core/` | 后端抽象、类型、几何、IO |
| `fc-cli` | `packages/cli/` | Click CLI 命令、输出格式化、插件、REPL |
| `fc-mcp` | `packages/mcp/` | FastMCP 服务器、MCP 工具注册 |
| `fc-runtime` | `packages/runtime/` | Agent 运行时: Planner, Executor, Corrector, BOM |

## AI 工程化体系 (M7)

基于《让 AI 熟练运用 FreeCAD CLI 的工程化方案》，建立完整的 AI 工具认知体系：

```
AI 工具认知 → 执行流程 → 约束规则 → 错误闭环
```

### 7 项工程化措施

1. **结构化工具清单** — `TOOL_SCHEMA.json` (17组/185命令)
2. **GUI→CLI 映射表** — 内嵌于 TOOL_SCHEMA.json
3. **Few-shot 示例库** — 5 个从简单到复杂的完整示例
4. **五阶段执行流模板** — 强制 AI 按流程执行
5. **命令历史上下文注入** — 执行结果反馈给 AI
6. **错误闭环自动学习** — 常见错误自动加入禁止规则
7. **Function calling schema** — 消灭语法错误

## 安全设计

- 路径遍历防护（`../`、双斜杠绕过、空字节注入）
- 名称白名单（仅 `[A-Za-z0-9_-]`）
- 导入路径必须存在，导出路径覆盖检查
- 84 个安全测试覆盖 12+ 种攻击向量
