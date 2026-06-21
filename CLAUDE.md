# CLAUDE.md — fc (Agent Native FreeCAD CLI)

> 当 AI Agent 在此项目目录下工作时，必须遵循以下规则。

## 项目概述

fc 是一个完整的 FreeCAD CLI 工具，提供 258+ 命令覆盖 17 个命令组，专为 AI Agent 设计。
内置 6 类标准 Agent 协同流水线（需求→设计→建模→审查→出图→标注），支持 LangGraph 风格控制图、经验库反馈回路和多零件装配。

**版本**: 0.9.0 | **路径**: D:\桌面文件\fc | **语言**: Python 3.12+

## 技能系统

完整的技能文件位于 `docs/skills/` 目录。每次 CAD 任务必须按需加载：

```
每次任务必读:
  ✅ docs/skills/CORE.md          — 五阶段执行流、全局规则、错误处理
  ✅ docs/skills/FUNDAMENTALS.md  — document/session/execute

按任务类型加载（选 1-2 个）:
  📦 创建几何体    → docs/skills/MODELING.md      — part/sketch/body
  ⚙️  工程分析/装配 → docs/skills/ENGINEERING.md   — assembly/fem/cam/material
  📐 出工程图      → docs/skills/DRAFTING.md      — techdraw/draft/spreadsheet
  💾 导入导出      → docs/skills/DATA_EXCHANGE.md — export/import/mesh/surface
```

## Agent 架构（0.9.0 新增）

项目实现了方法论要求的 6 类标准 Agent，通过 LangGraph 风格控制图编排：

```
用户输入
   └── AgentGraph（LangGraph 风格控制图）
         ├─ requirement_node → 需求解析 Agent（RequirementAgent）
         ├─ design_node      → 设计规划 Agent（DesignAgent）
         ├─ modeling_node    → CAD 建模 Agent（CADModelingAgent）
         ├─ review_node      → 几何审查 Agent（GeometryReviewAgent）←─┐ 条件回滚
         ├─ drafting_node    → 出图 Agent（DraftingAgent）
         └─ annotation_node  → 标注合规 Agent（AnnotationComplianceAgent）─┘ 条件回滚
               │
               └── FeedbackLoop ── ExperienceLibrary (JSONL)
                    pre_run: 推荐历史经验
                    post_run: 记录新经验
```

### 核心模块

| 模块 | 路径 | 职责 |
|------|------|------|
| agent_schemas | `fc_runtime/agent_schemas.py` | 所有 Agent 的 Pydantic IO Schema |
| agent_graph | `fc_runtime/agent_graph.py` | LangGraph 风格控制图（节点/边/条件分支） |
| orchestrator | `fc_runtime/orchestrator.py` | 状态机编排器（超时+trace+handshake） |
| requirement_agent | `fc_runtime/requirement_agent.py` | 需求解析 Agent |
| design_agent | `fc_runtime/design_agent.py` | 设计规划 Agent |
| modeling_agent | `fc_runtime/modeling_agent.py` | CAD 建模 Agent |
| geometry_review_agent | `fc_runtime/geometry_review_agent.py` | 几何审查 Agent（7项检查） |
| drafting_agent | `fc_runtime/drafting_agent.py` | 出图 Agent |
| annotation_agent | `fc_runtime/annotation_agent.py` | 标注合规 Agent（7项检查） |
| experience_library | `fc_runtime/experience_library.py` | 知识库/经验库 + 反馈回路 |
| assembly | `fc_runtime/assembly.py` | 多零件装配（AssemblyAgent + AssemblyExecutor） |
| standard_library | `fc_runtime/standard_library.py` | 标准零件库（螺栓/轴承/法兰等） |
| agent_handshake | `fc_runtime/agent_handshake.py` | Agent IO Schema 握手验证 |
| agent_logging | `fc_runtime/agent_logging.py` | 统一结构化日志 |

## MCP 服务器

fc 提供 MCP 服务器 (`fc-mcp`)，注册为 `freecad` 服务器，包含 6 个工具模块：
- **document** — 文档生命周期
- **geometry** — 几何体创建与编辑
- **sketch** — 2D 草图
- **export** — 文件导出
- **execute** — Python 代码执行
- **query** — 查询与信息

## CLI 使用

```bash
# 所有命令必须使用 --json 输出
fc document new --name MyPart --json
fc part add box --name Box --param Length=20 --param Width=15 --param Height=10 --json
fc export step --output model.step --json
```

### fc agent — Agent 流水线（0.9.0 新增）

```bash
# 一句话出图：需求→设计→建模→审查→出图→标注 全流程
fc agent pipeline "一个长100mm宽50mm高25mm的盒子，Q235钢"

# 其他子命令：library / handshake / explain
# 详细用法见 .claude/skills/fc/SKILL.md
```

## 五阶段执行流（不可跳过）

1. **工具选择** — 列出所有需要的命令组和命令
2. **任务分解** — 拆分为原子步骤，每步一条 CLI 命令
3. **坐标与依赖** — 计算坐标，标识依赖元素
4. **依赖验证** — 检查所有依赖有效（无悬空引用，无循环依赖）
5. **命令输出** — 按顺序输出 CLI 命令，附带注释

## 核心规则

1. 始终使用 `--json`
2. 唯一命名：`{类型}_{序号}`（如 `Box_001`, `Cylinder_001`）
3. 只引用已创建的元素
4. 多步工作流用 `--project`
5. 每批 ≤10 命令
6. 先 `document new` 再建模
7. 所有尺寸单位：毫米（mm）

## 项目结构

```
packages/
  core/     — fc_core: BackendInterface, HeadlessBackend, RPCBackend
  cli/      — fc_cli: Click 命令组 (258+ 命令)
  mcp/      — fc_mcp: FastMCP 服务器
  runtime/  — fc_runtime: Planner, Executor, Corrector + Agent 架构（6类Agent + LangGraph + 经验库 + 装配）
  test/     测试工具
```

## 测试

```bash
# 运行 runtime 测试（含 Agent 架构全部测试）
pytest packages/runtime/tests/ -v

# 运行 core 测试
pytest packages/core/tests/ -v

# 全量测试
pytest packages/core/tests/ packages/runtime/tests/ -v
```

当前测试状态：**755 passed**（core 146 + runtime 507 + cli 52 + mcp 50）

## 参考文档

- `docs/TOOL_SCHEMA.json` — 机器可读命令 schema
- `docs/FUNCTION_SCHEMAS.json` — Function calling 定义
- `docs/EXECUTION_FLOW_TEMPLATE.md` — 五阶段模板
- `docs/AI_AGENT_GUIDE.md` — AI Agent 完整指南
- `docs/ERROR_RULES.md` — 错误规则（自动学习生成）
