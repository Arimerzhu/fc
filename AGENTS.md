# AGENTS.md — fc Agent Team

> Agent Team 架构、职责分配和协作协议。

## Team: fc-team

**描述**: Agent Native FreeCAD CLI development team. 7 agents coordinated by Chief Architect.

## Agent 架构

```
Chief Architect (监督)
    │
    ├── fc-core-agent (blue)    ← packages/core/
    ├── fc-cli-agent (green)    ← packages/cli/
    ├── fc-mcp-agent (cyan)    ← packages/mcp/
    ├── fc-runtime-agent (magenta) ← packages/runtime/
    ├── fc-test-agent (yellow)  ← packages/*/tests/
    └── fc-review-agent (red)   ← 代码审查
```

## Agent 详情

| Agent | 模型 | 颜色 | 职责 | 配置 |
|-------|------|------|------|------|
| **Chief Architect** | opus | — | 架构设计、任务分配、验收、文档维护 | 主会话 |
| **fc-core-agent** | opus | 🔵 blue | BackendInterface, HeadlessBackend, RPCBackend, 类型系统, 几何, IO | `.claude/agents/fc-core-agent.md` |
| **fc-cli-agent** | opus | 🟢 green | Click 命令组 (17组), OutputManager, 全局选项 | `.claude/agents/fc-cli-agent.md` |
| **fc-mcp-agent** | opus | 🔵 cyan | FastMCP 服务器, MCP 工具 (6模块~50工具) | `.claude/agents/fc-mcp-agent.md` |
| **fc-runtime-agent** | opus | 🟣 magenta | Planner, Executor, Corrector, BOM, agent_cmd, 6类Agent, LangGraph, 经验库, 装配 | `.claude/agents/fc-runtime-agent.md` |
| **fc-test-agent** | opus | 🟡 yellow | 单元测试, 集成测试, E2E 测试, Mock Backend | `.claude/agents/fc-test-agent.md` |
| **fc-review-agent** | opus | 🔴 red | 架构审查, 安全审查, 接口一致性, 文档质量 | `.claude/agents/fc-review-agent.md` |

## 协作协议

### 任务分配流程

```
1. Chief Architect 分析需求
2. 更新 PROJECT.md / TASKS.md
3. 创建 Task 并分配给对应 Agent
4. Agent 执行任务
5. fc-review-agent 审查结果
6. Chief Architect 验收
7. 更新项目文档
```

### 依赖关系

```
fc-core-agent → 无依赖（基础层）
fc-cli-agent  → 依赖 fc-core-agent（使用 BackendInterface）
fc-mcp-agent  → 依赖 fc-core-agent（使用 BackendInterface）
fc-runtime-agent → 依赖 fc-cli-agent（通过 CLI 子进程执行）
fc-test-agent → 依赖所有 agent（测试所有模块）
fc-review-agent → 依赖所有 agent（审查所有代码）
```

### 通信协议

- **Chief Architect → Agent**: 通过 `Agent` tool 发送任务
- **Agent → Chief Architect**: 通过返回值报告结果
- **Agent ↔ Agent**: 通过 `SendMessage` 通信（需要时）
- **审查流程**: fc-review-agent 输出审查报告，Chief Architect 决定是否接受

### 文件权限

| Agent | 可读取 | 可写入 |
|-------|--------|--------|
| fc-core-agent | `packages/core/` | `packages/core/` |
| fc-cli-agent | `packages/cli/`, `packages/core/` | `packages/cli/` |
| fc-mcp-agent | `packages/mcp/`, `packages/core/` | `packages/mcp/` |
| fc-runtime-agent | `packages/runtime/`, `packages/cli/` | `packages/runtime/` |
| fc-test-agent | `packages/*/tests/` | `packages/*/tests/` |
| fc-review-agent | 所有文件 | 只读（审查不修改） |

## 使用方式

### 分配任务给特定 Agent

```
# 在 Claude Code 会话中：
/agent fc-core-agent "在 BackendInterface 中添加 body_mirror 方法"
/agent fc-cli-agent "为 sketch 命令组添加 add-ellipse 命令"
/agent fc-test-agent "为 fc_core/backend 编写单元测试"
/agent fc-review-agent "审查 packages/cli/src/fc_cli/commands/part.py 的架构一致性"
```

### 并行执行

多个独立任务可同时分配给不同 Agent：

```
Agent 1 (fc-core-agent): 实现新后端方法
Agent 2 (fc-cli-agent): 添加对应 CLI 命令
Agent 3 (fc-mcp-agent): 添加对应 MCP 工具
```

## 当前任务分配

| 任务 | 分配 | 状态 |
|------|------|------|
| TASK-009: FreeCAD 集成测试 | fc-test-agent | 🔲 待启动（需真实 FreeCAD） |
| TASK-010: CLI 命令测试 | fc-test-agent | ✅ 完成（20 tests, document 命令组） |
| TASK-011: MCP 工具测试 | fc-test-agent | ✅ 完成（50 tests, geometry 工具） |
| TASK-012: 插件系统 | fc-core-agent + fc-cli-agent | 🔲 待启动 |
| TASK-013: SKILL.md | fc-mcp-agent | 🔲 待启动 |
| TASK-014: REPL 模式 | fc-cli-agent | 🔲 待启动 |
| TASK-015: P0 致命缺陷修复 | fc-runtime-agent | ✅ 完成（Agent Schema + 需求Agent + 错误分类 + 几何校验, 60 tests） |
| TASK-016: P1 重要缺陷修复 | fc-runtime-agent | ✅ 完成（设计Agent + 建模Agent + 出图Agent + 编排器, 64 tests） |
| TASK-017: P2 优化项 | fc-runtime-agent | ✅ 完成（日志 + 握手 + 标准库 + CLI集成, 44 tests） |
| TASK-018: P3 架构完善 | fc-runtime-agent | ✅ 完成（几何审查Agent + 标注Agent + LangGraph + 经验库 + 装配, 44 tests） |

## 测试结果汇总（2026-06-19）

| 包 | 测试数 | 状态 | Agent |
|----|--------|------|-------|
| `packages/core/tests/` | 146 | ✅ 全通过 | fc-test-agent |
| `packages/runtime/tests/` | 507 | ✅ 全通过 | fc-runtime-agent |
| `packages/cli/tests/` | 52 | ✅ 全通过 | fc-cli-agent |
| `packages/mcp/tests/` | 50 | ✅ 全通过 | fc-mcp-agent |
| **总计** | **755** | **✅ 全通过** | — |

### P0-P3 新增测试覆盖（2026-06-19）

| 阶段 | 测试文件 | 测试数 | 覆盖内容 |
|------|---------|--------|---------|
| P0 | `test_p0_critical.py` | 60 | Agent Schema, 需求解析, 错误分类, 几何校验 |
| P1 | `test_p1_important.py` | 64 | 设计规划, CAD建模, 出图, 编排器全流程 |
| P2 | `test_p2_integration.py` | 44 | 结构化日志, Schema握手, 标准件库, CLI集成 |
| P3 | `test_p3_full.py` | 44 | 几何审查Agent, 标注合规Agent, AgentGraph, 经验库, 装配 |

### P0-P3 新增模块

| 模块 | 阶段 | 职责 |
|------|------|------|
| `agent_schemas.py` | P0 | 6类Agent的Pydantic IO Schema |
| `requirement_agent.py` | P0 | 需求解析Agent（自然语言→RequirementDocument） |
| `error_classifier.py` | P0 | 三级错误分类器（DESIGN/CODE/DRAWING） |
| `geometry_validator.py` | P0 | 几何拓扑校验器 |
| `design_agent.py` | P1 | 设计规划Agent（RequirementDocument→ModelingPlan） |
| `modeling_agent.py` | P1 | CAD建模Agent（ModelingPlan→FreeCAD脚本） |
| `drafting_agent.py` | P1 | 出图Agent（RequirementDocument→DrawingOutput） |
| `orchestrator.py` | P1 | 状态机编排器（超时+trace+handshake+dry_run） |
| `agent_logging.py` | P2 | 统一结构化日志（stage/task/error/io事件） |
| `agent_handshake.py` | P2 | Agent IO Schema握手验证 |
| `standard_library.py` | P2 | 标准零件库（螺栓/轴承/法兰等15+预设） |
| `geometry_review_agent.py` | P3 | 独立几何审查Agent（7项拓扑检查） |
| `annotation_agent.py` | P3 | 独立标注合规Agent（7项规范检查） |
| `agent_graph.py` | P3 | LangGraph风格控制图（节点/边/条件分支） |
| `experience_library.py` | P3 | 知识库/经验库 + 反馈回路 |
| `assembly.py` | P3 | 多零件装配（AssemblyAgent + AssemblyExecutor） |
