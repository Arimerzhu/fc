# 决策记录

本项目的重要架构决策记录（ADR）。

## 最新决策

### ADR-024: Function Calling Schema 生成 (TASK-037)

为所有 185 个 CLI 命令生成 OpenAI Function Calling 定义，AI 通过结构化参数调用，消灭语法错误。

### ADR-023: 错误闭环自动学习设计 (TASK-036)

新建 `error_rules.py`，8 种错误模式自动提取，同一模式 ≥3 次自动生成禁止规则，支持跨会话持久化。

### ADR-022: 五阶段执行流实现方案 (TASK-032)

强制 AI 按五阶段流程执行，新增 DFS 三色标记法循环依赖检测，阶段完整性校验。

### ADR-021: AI 工程化体系设计 (M7)

采用 7 项工程化措施，将 AI 从"会写命令"升级为"会用工具"。

### ADR-018: 结构化 JSON 工具清单 (TASK-030)

生成 `TOOL_SCHEMA.json`，包含 17 命令组、185 命令、26 错误码、31 个 GUI→CLI 映射。

### ADR-017: E2E Agent 测试 Bug 修复 (TASK-028)

修复 5 个 bug（2 个 P0 + 3 个 P1），`fc agent` 完整流程可执行。

### ADR-016: Test Coverage Strategy

三层测试策略：MockBackend 单元测试 + 集成测试 + E2E 测试。

### ADR-015: Backend Geometry Deduplication

通过 Mixin 继承消除 ~300 行重复代码。

### ADR-014: HeadlessBackend 批量执行模式

batch_start/add/execute 方法，多步操作一次进程调用完成。

### ADR-013: Agent Team Architecture

6 个专用 Agent + Chief Architect 监督的架构。

### ADR-012: Pattern-Matching Planner

基于正则和关键词模板的规划器，零延迟零成本。

### ADR-011: Subprocess-per-Operation

每次操作启动新 FreeCADCmd 进程，简单可靠。

### ADR-010: ToolResponse Standard Format

统一响应格式：status, operation, data, message, error_code, suggestion。

### ADR-006: Monorepo with uv Workspace

单体仓库 + uv workspace + Hatch 构建系统。

### ADR-005: FastMCP for MCP Server

使用官方 MCP Python SDK。

### ADR-004: Click for CLI Framework

使用 Click 框架构建所有 CLI 命令。

### ADR-003: Macro-Based Headless Execution

通过临时 Python 脚本 + FreeCADCmd 子进程执行。

### ADR-002: Dual Backend Architecture

HeadlessBackend + RPCBackend 双后端。

### ADR-001: Python as Sole Language

纯 Python 3.12+ 开发。
