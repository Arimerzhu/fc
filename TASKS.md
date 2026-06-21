# TASKS.md — fc Task Breakdown

> Single Source of Truth for task tracking.
> Chief Architect 维护。所有任务必须有 ID / Goal / Dependencies / Deliverables / Acceptance Criteria。

## 任务状态图

```
M1-M5 ✅ → M6 ✅ → M7 ✅ 100% → M8 ✅ V1.0发布
```

---

## Active Tasks

### TASK-029: 性能基准测试 + 路径遍历防护 ✅ COMPLETED
- **ID**: TASK-029
- **Goal**: 测量 HeadlessBackend subprocess 开销 baseline；系统化路径遍历防护
- **Priority**: P1
- **Status**: ✅ 已完成 (2026-06-11)
- **Deliverables**:
  - `packages/core/src/fc_core/security.py` — 安全验证模块 (validate_name/validate_path/validate_export_path/validate_import_path/SecurityError)
  - `packages/core/tests/test_security.py` — 84 个安全测试
  - `packages/core/tests/test_benchmarks.py` — 7 个性能基准测试
  - 修改 export.py / import_cmd.py / execute.py 添加路径验证
- **Acceptance Criteria**:
  - ✅ 84 安全测试通过（路径遍历、名称验证、导入/导出验证）
  - ✅ 7 基准测试通过（document_new=334ms, object_create=708ms, export=730ms）
  - ✅ Batch vs Sequential 加速比 4.86x
  - ✅ 路径遍历攻击被拦截（../../ 等）
  - ✅ 413 core tests passed, 零回归

### TASK-030: AI 工程化增强 — 结构化工具清单 ✅ COMPLETED
- **ID**: TASK-030
- **Goal**: 生成机器可读的全量 CLI 命令 JSON schema，让 AI Agent 100% 吃透工具集
- **Priority**: P1
- **Status**: ✅ 已完成 (2026-06-11)
- **Dependencies**: M5 完成
- **Deliverables**:
  - `docs/TOOL_SCHEMA.json` — 17 命令组, 185 命令, 26 错误码, 31 GUI 映射 (63KB)
  - GUI→CLI 映射内嵌于 TOOL_SCHEMA.json
- **Acceptance Criteria**:
  - ✅ 每个命令有：功能、参数、返回值、示例
  - ✅ 覆盖全部 17 个命令组
  - ✅ AI Agent 可通过读取 TOOL_SCHEMA.json 自动发现所有命令

### TASK-031: AI 工程化增强 — Few-shot 示例库 ✅ COMPLETED
- **ID**: TASK-031
- **Goal**: 建立 5 个从简单到复杂的完整示例，让 AI 模仿风格和流程
- **Priority**: P2
- **Status**: ✅ 已完成 (2026-06-11)
- **Deliverables**:
  - `docs/examples/01_simple_box_with_hole.md` — 简单：底板通孔
  - `docs/examples/02_mounting_bracket.md` — 中等：带凸台倒角安装支架
  - `docs/examples/03_simple_assembly.md` — 中等：底座+支柱装配体
  - `docs/examples/04_parametric_design.md` — 中等：参数化盒子
  - `docs/examples/05_full_workflow.md` — 复杂：从需求到工程图
- **Acceptance Criteria**:
  - ✅ 5 个示例文件全部创建
  - ✅ 每个示例严格遵循五阶段执行流模板
  - ✅ 所有命令示例使用 --json 格式
  - ✅ 坐标计算过程清晰完整
  - ✅ 依赖关系正确

### TASK-032: AI 工程化增强 — 五阶段执行流模板 ✅ COMPLETED
- **ID**: TASK-032
- **Goal**: 将工程化方案中的五阶段执行流模板化，增强 Planner
- **Priority**: P2
- **Status**: ✅ 已完成 (2026-06-11)
- **Dependencies**: TASK-030, TASK-031
- **Deliverables**:
  - `docs/EXECUTION_FLOW_TEMPLATE.md` — 五阶段执行流模板（已存在，内容完整）
  - 更新 `fc_runtime/planner.py` — Plan 类新增 `_validate_phase_completeness()` 方法，Phase 4 新增循环依赖检测（DFS）
  - 更新 `SKILL.md` — 新增 "Five-Phase Execution Flow" 章节 + Tips 13-17
  - `packages/runtime/tests/test_five_phase.py` — 新增 4 个测试（completeness check + circular dep detection）
- **Acceptance Criteria**:
  - ✅ 强制 AI 按流程执行：工具选型 → 任务拆解 → 坐标与依赖计算 → 依赖校验 → 命令输出
  - ✅ 跳过任何一步都算失败（`_validate_phase_completeness()` 校验）
  - ✅ 循环依赖检测（DFS 三色标记法）
  - ✅ 16/16 five-phase 测试通过，224/224 runtime 测试零回归

### TASK-035: AI 工程化增强 — 命令历史上下文注入 ✅ COMPLETED
- **ID**: TASK-035
- **Goal**: 实现执行结果反馈机制，让 AI 基于已创建元素继续后续操作
- **Priority**: P2
- **Status**: ✅ 已完成 (2026-06-11)
- **Dependencies**: TASK-032
- **Deliverables**:
  - 更新 `fc_runtime/executor.py` — 新增 ElementSummary、BatchContext 数据类；Executor 新增分批执行 + 上下文注入方法
  - `docs/CONTEXT_INJECTION_PROTOCOL.md` — 上下文注入协议文档
  - `packages/runtime/tests/test_context_injection.py` — 18 个上下文注入测试
- **Acceptance Criteria**:
  - ✅ 每执行 batch_size 条命令后，自动生成元素摘要
  - ✅ 摘要包含：元素名称、类型、坐标、尺寸、拓扑关系
  - ✅ 后续任务只能引用已创建的元素（`validate_element_reference()`）
  - ✅ 支持分批执行复杂任务（>10 条命令自动分段）
  - ✅ 246/246 runtime 测试零回归

### TASK-036: AI 工程化增强 — 错误闭环自动学习 ✅ COMPLETED
- **ID**: TASK-036
- **Goal**: 建立自动修正闭环，常见错误自动加入禁止规则
- **Priority**: P2
- **Status**: ✅ 已完成 (2026-06-11)
- **Dependencies**: TASK-032
- **Deliverables**:
  - `packages/runtime/src/fc_runtime/error_rules.py` — ErrorRulesEngine (ErrorPattern/ForbiddenRule/规则生成/持久化)
  - 更新 `packages/runtime/src/fc_runtime/corrector.py` — 集成 ErrorRulesEngine，analyze() 自动记录错误
  - `docs/ERROR_RULES.md` — 禁止规则文档（自动维护）
  - `packages/runtime/tests/test_error_rules.py` — 41 个测试
  - 更新 `SKILL.md` — 新增 Tip 18 引用动态错误规则
- **Acceptance Criteria**:
  - ✅ CLI 执行报错时，自动分析错误原因并记录到 rules engine
  - ✅ 高频错误（≥3次相同模式）自动加入禁止规则
  - ✅ 修正后的命令重新执行，直到成功或超过重试次数
  - ✅ 错误规则可导出/导入（跨会话持久化）
  - ✅ 287/287 runtime 测试零回归

### TASK-037: AI 工程化增强 — Function Calling Schema ✅ COMPLETED
- **ID**: TASK-037
- **Goal**: 为每个 CLI 命令生成函数调用定义，消灭语法错误
- **Priority**: P2
- **Status**: ✅ 已完成 (2026-06-11)
- **Dependencies**: TASK-030
- **Deliverables**:
  - `docs/FUNCTION_SCHEMAS.json` — 185 个 OpenAI function calling 定义
  - `scripts/generate_function_schemas.py` — 从 TOOL_SCHEMA.json 自动生成
- **Acceptance Criteria**:
  - ✅ 每个 CLI 命令对应一个 function 定义
  - ✅ 包含 name、description、parameters (JSON Schema)
  - ✅ required 参数正确标注
  - ✅ AI 通过函数调用生成结构化参数，无语法/顺序/拼写错误
  - ✅ 与 TOOL_SCHEMA.json 保持同步

### TASK-033: 文档网站 (MkDocs) ✅ COMPLETED
- **ID**: TASK-033
- **Goal**: 建立项目文档网站
- **Priority**: P2
- **Status**: ✅ 已完成 (2026-06-11)
- **Dependencies**: TASK-030, TASK-031, TASK-032
- **Deliverables**:
  - `mkdocs.yml` — MkDocs 配置（Material 主题，中文，搜索）
  - `docs_mkdocs/` — 完整文档目录（首页/快速入门/安装/命令参考/AI集成/MCP/API/架构/路线图/决策）
  - 17 个命令组参考页面
  - 5 个示例页面
  - Agent 集成页面（SKILL/执行流/上下文注入/错误规则/Function Calling）
- **Acceptance Criteria**:
  - ✅ 包含：安装指南、快速入门、命令参考、MCP 配置、Agent 集成、示例、API 文档
  - ✅ `mkdocs build --strict` 零警告通过
  - ✅ Material 主题，中文界面，搜索功能

### TASK-034: CI 集成测试 ✅ COMPLETED
- **ID**: TASK-034
- **Goal**: 在 CI 中运行 FreeCAD 集成测试
- **Priority**: P2
- **Status**: ✅ 已完成 (2026-06-11)
- **Dependencies**: TASK-029
- **Deliverables**:
  - `.github/workflows/ci.yml` — CI 工作流（lint + unit tests + integration tests + docs build）
- **Acceptance Criteria**:
  - ✅ CI 自动运行单元测试（core/cli/mcp/runtime）
  - ✅ CI 自动运行集成测试（需要 FreeCAD，Windows runner）
  - ✅ CI 自动构建文档网站
  - ✅ Lint 检查（ruff check + ruff format）
  - ✅ 测试失败时 PR 无法合并

---

## Completed Tasks

| ID | Goal | Completed | Deliverables |
|----|------|-----------|-------------|
| TASK-000 | Project scaffolding | 2026-06-09 | Monorepo, pyproject.toml, CI |
| TASK-001 | Architecture documents | 2026-06-09 | PROJECT.md, ARCHITECTURE.md, ROADMAP.md, TASKS.md, DECISIONS.md |
| TASK-002 | Backend geometry operations | 2026-06-09 | PrimitivesMixin, GeometryOpsMixin |
| TASK-003 | MCP tool implementation (~50 tools) | 2026-06-10 | 6 modules, ~50 tools |
| TASK-004 | Agent Runtime (Planner/Executor/Corrector/BOM) | 2026-06-10 | planner.py, executor.py, corrector.py, bom.py, agent_cmd.py |
| TASK-005 | Engineering modules (17 command groups) | 2026-06-10 | 17 command group files |
| TASK-006 | IO modules (export presets, import auto-detect) | 2026-06-10 | export.py, import_mod.py |
| TASK-007 | Session management (undo/redo/snapshot/restore) | 2026-06-10 | session_cmd.py |
| TASK-008 | Core unit tests (54 tests) | 2026-06-10 | test_types.py, test_backend.py, test_geometry.py |
| TASK-009 | FreeCAD 1.1.1 Integration Test (25 tests) | 2026-06-10 | test_integration_full.py |
| TASK-010 | CLI Command Tests (17/17 groups, 540 tests) | 2026-06-10 | 17 test files in packages/cli/tests/ |
| TASK-011 | MCP Tool Tests (6/6 modules, 268 tests) | 2026-06-10 | 6 test files in packages/mcp/tests/ |
| TASK-012 | Plugin system | 2026-06-10 | plugins.py, hello_plugin.py, test_plugins.py |
| TASK-013 | SKILL.md for AI Agents | 2026-06-10 | SKILL.md (476 lines) + 12 command-group SKILL files |
| TASK-014 | REPL mode | 2026-06-10 | repl.py, test_repl.py |
| TASK-015 | HeadlessBackend batch mode | 2026-06-10 | batch_start/add/execute, test_batch.py (24 tests) |
| TASK-016 | Security + interface fixes | 2026-06-10 | Snapshot path traversal fix, ToolResponse format fix |
| TASK-017 | CLI test coverage expansion | 2026-06-10 | 10 command groups tested (240 tests) |
| TASK-018 | MCP test coverage expansion | 2026-06-10 | 6 modules tested (268 tests) |
| TASK-021 | RPCBackend.export() P0 bug fix | 2026-06-10 | Fixed undefined `code` variable + added execute_code() |
| TASK-022 | Backend geometry deduplication | 2026-06-10 | GeometryOpsMixin inheritance, ~300 lines removed |
| TASK-023 | Integration test framework | 2026-06-10 | 8 tests with FreeCAD skip markers |
| TASK-024 | Corrector/BOM extended tests | 2026-06-10 | 45 edge case tests |
| TASK-025 | _build_wrapper_script indentation P0 fix | 2026-06-10 | Fixed body outside try: block |
| TASK-026 | Runtime test failures fix | 2026-06-10 | 14/14 pre-existing failures resolved |
| TASK-027 | 3 source code bug fixes | 2026-06-10 | surface.py NameError, spreadsheet.py/material.py param mismatch |
| TASK-028 | E2E Agent tests (28 tests ALL PASSED) | 2026-06-11 | test_e2e_agent.py, E2E_AGENT_TEST_REPORT.md |
| TASK-029 | Performance benchmarks + path traversal protection | 2026-06-11 | security.py, test_security.py (84), test_benchmarks.py (7) |
| TASK-030 | Structured tool inventory (TOOL_SCHEMA.json) | 2026-06-11 | docs/TOOL_SCHEMA.json — 17 groups, 185 commands |
| TASK-031 | Few-shot example library (5 examples) | 2026-06-11 | docs/examples/01-05 |
| TASK-032 | Five-phase execution flow template | 2026-06-11 | planner.py (_validate_phase_completeness), test_five_phase.py |
| TASK-035 | Command history context injection | 2026-06-11 | executor.py (ElementSummary/BatchContext), test_context_injection.py (18) |
| TASK-036 | Error closed-loop auto-learning | 2026-06-11 | error_rules.py (ErrorRulesEngine), corrector.py integration, test_error_rules.py (41) |
| TASK-037 | Function calling schema generation | 2026-06-11 | FUNCTION_SCHEMAS.json (185 functions), generate_function_schemas.py |

---

## Task Dependency Graph

```
TASK-000 → TASK-001 → TASK-002 → TASK-003/004/005/006/007 → TASK-008
                                                                    ↓
TASK-009 → TASK-010 → TASK-011 → TASK-012 → TASK-013 → TASK-014
  ↓         ↓          ↓
TASK-015  TASK-017   TASK-018
  ↓         ↓          ↓
TASK-016 → TASK-021 → TASK-022 → TASK-023 → TASK-024 → TASK-025 → TASK-026 → TASK-027 → TASK-028
                                                                                        ↓
                                                                              TASK-029 → TASK-030 → TASK-031 → TASK-032 → TASK-035 → TASK-036 → TASK-037
                                                                                        ↓
                                                                              TASK-034
```
