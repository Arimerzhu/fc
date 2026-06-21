# DECISIONS.md — Architecture Decision Records

> Single Source of Truth for architectural decisions.
> Chief Architect 维护。每个 ADR 包含：Date / Status / Context / Decision / Consequences。

---

---

## ADR-022: 五阶段执行流实现方案 (TASK-032)

- **Date**: 2026-06-11
- **Status**: Accepted
- **Context**: 工程化方案要求强制 AI 按五阶段流程执行，跳过任何一步都算失败。需要将此约束编码到 Planner 中。
- **Decision**:
  1. `docs/EXECUTION_FLOW_TEMPLATE.md` 已存在且内容完整，定义了五阶段的输出格式和规则
  2. `Plan.to_five_phase_report()` 输出完整五阶段报告，末尾附加 `_validate_phase_completeness()` 校验
  3. Phase 4 增强：新增 DFS 三色标记法循环依赖检测（WHITE→GRAY→BLACK）
  4. SKILL.md 新增 "Five-Phase Execution Flow" 章节，Tips 13-17 引用五阶段规则
  5. `agent_cmd.py` 已在第 92-96 行调用 `plan.to_five_phase_report()` 输出
- **Completeness Check 逻辑**:
  - Phase 1: 至少有一个 task
  - Phase 2: 所有 task 有 description
  - Phase 3: 至少一个 task 有 phase3_coords 或 params
  - Phase 4: 所有 dependency 指向存在的 task
  - Phase 5: 所有 task 有 command 字段
- **Consequences**:
  - ✅ 16/16 five-phase 测试通过
  - ✅ 224/224 runtime 测试零回归
  - ✅ 循环依赖可被自动检测并报告
  - ✅ `fc agent` 输出自动包含五阶段报告 + completeness check

## ADR-021: AI 工程化体系设计 (M7)

- **Date**: 2026-06-11
- **Status**: Accepted
- **Context**: 基于《让 AI 熟练运用 FreeCAD CLI 的工程化方案》，需要建立完整的 AI 工具认知体系，将 AI 从"会写命令"升级为"会用工具"。
- **Decision**: 采用 7 项工程化措施，分 4 个 TASK 实施：
  1. **结构化工具清单** (TASK-030 ✅) — TOOL_SCHEMA.json，机器可读的全量命令 schema
  2. **GUI→CLI 映射表** (TASK-030 ✅) — 自然语言意图到命令的映射
  3. **Few-shot 示例库** (TASK-031 ✅) — 5 个从简单到复杂的完整示例
  4. **五阶段执行流模板** (TASK-032) — 强制 AI 按流程执行
  5. **命令历史上下文注入** (TASK-035) — 执行结果反馈给 AI，解决上下文失忆
  6. **错误闭环自动学习** (TASK-036) — 常见错误自动加入禁止规则
  7. **Function calling schema** (TASK-037) — 消灭语法错误
- **核心原则**:
  - 所有元素必须指定唯一名称，格式：`{类型}_{序号}`
  - 严格遵循 FreeCAD 绘图时序：创建基准 → 创建基础几何体 → 布尔运算 → 添加约束 → 导出
  - 绝对不允许合并多个操作到一条命令中
  - 复杂任务拆分为多个小任务，每完成 5-10 条命令就反馈一次执行结果
- **Consequences**:
  - ✅ AI Agent 可通过 TOOL_SCHEMA.json 自动发现所有 185 个命令
  - ✅ 五阶段模板强制结构化输出，跳过任何一步都算失败
  - ✅ Few-shot 示例让 AI 学习命令调用风格和流程
  - ✅ 上下文注入解决 AI 失忆问题（TASK-035）
  - ✅ 错误闭环让 AI 越用越聪明（TASK-036）
  - ✅ Function calling 彻底消灭语法错误（TASK-037）

---

## ADR-023: 错误闭环自动学习设计 (TASK-036)

- **Date**: 2026-06-11
- **Status**: Accepted
- **Context**: Corrector 已有 7 种错误模式的修正能力，但每次都从零开始分析，无法积累经验。需要让 AI 越用越聪明。
- **Decision**:
  1. 新建 `error_rules.py`，核心类 `ErrorRulesEngine`
  2. 8 种错误模式提取：`missing_flag`, `invalid_value`, `negative_dimension`, `unknown_object`, `missing_document`, `file_exists`, `wrong_type`, `missing_param`
  3. 同一模式出现 >= 3 次（可配置阈值）→ 自动生成 `ForbiddenRule`
  4. 规则持久化：JSON 导出/导入 + Markdown 文档 (`docs/ERROR_RULES.md`)
  5. `corrector.py` 集成：`analyze()` 每分析一个错误就 `record_error()` 到 engine
  6. `Corrector.get_rules_text()` 输出活跃规则，可注入 Planner 提示词
- **错误模式提取逻辑**:
  - 正则匹配从 error + stderr 中提取结构化信息
  - normalize：lowercase、压缩空白、剥离时间戳
  - 模式 hash = MD5(pattern_type + sorted_context_keys) 前12位
- **规则生成策略**:
  - 每种 pattern 类型有对应的 `RULE_GENERATORS` lambda
  - 生成 `ForbiddenRule` 包含 rule_id、forbidden_action、suggested_fix
  - rule_id 格式：`{PATTERN}_{CONTEXT_VALUE}` (e.g., `MISSING_FLAG_NAME`)
- **Consequences**:
  - ✅ 41/41 error rules 测试通过
  - ✅ 287/287 runtime 测试零回归
  - ✅ 跨会话规则持久化（export/import JSON）
  - ✅ 人类可读的 ERROR_RULES.md 自动生成

---

## ADR-024: Function Calling Schema 生成 (TASK-037)

- **Date**: 2026-06-11
- **Status**: Accepted
- **Context**: AI Agent 直接用自然语言拼 CLI 参数容易出语法错误（顺序、拼写、遗漏 required）。OpenAI Function Calling 可通过结构化参数消除这类错误。
- **Decision**:
  1. 创建 `scripts/generate_function_schemas.py`，从 TOOL_SCHEMA.json 自动生成
  2. 输出 `docs/FUNCTION_SCHEMAS.json` — 185 个 function 定义
  3. 每个 function 包含：name、description、parameters (JSON Schema)、required、example
  4. 类型映射：STR→string, INT→integer, FLOAT→number, FLAG→boolean, `A|B|C`→enum
- **Consequences**:
  - ✅ 185 function definitions 全部生成
  - ✅ AI 通过函数调用生成结构化参数，无语法错误
  - ✅ 与 TOOL_SCHEMA.json 保持同步（重新运行脚本即可）

- **Date**: 2026-06-11
- **Status**: Accepted
- **Context**: 需要系统化路径遍历防护，防止 AI Agent 或用户输入恶意路径。
- **Decision**: 创建 `packages/core/src/fc_core/security.py` 安全模块，提供 `validate_name()`、`validate_path()`、`validate_export_path()`、`validate_import_path()` 四个验证函数和 `SecurityError` 异常类。
- **覆盖范围**:
  - 路径遍历攻击（`../`、`..\`、双斜杠绕过、空字节注入）
  - 非法字符（`< > | ? * " :`）
  - 名称白名单（仅 `[A-Za-z0-9_-]`）
  - 导入路径必须存在，导出路径覆盖检查
- **集成点**: export.py、import_cmd.py、execute.py 全部添加路径验证
- **Consequences**:
  - ✅ 84 个安全测试覆盖 12+ 种攻击向量
  - ✅ SecurityError 包含 code 和 suggestion，AI Agent 可自动恢复
  - ✅ 零回归（413 core tests passed）

---

## ADR-020: Few-shot 示例库设计 (TASK-031)

- **Date**: 2026-06-11
- **Status**: Accepted
- **Context**: 工程化方案要求 3-5 个从简单到复杂的完整示例，让 AI 模仿风格和流程。
- **Decision**: 创建 5 个 Markdown 示例文件，每个严格遵循五阶段执行流模板（工具选型→任务拆解→坐标与依赖计算→依赖校验→命令输出）。
- **难度梯度**: 简单(6步) → 中等(13步) → 中等(21步) → 中等(17步) → 复杂(22步)
- **Consequences**:
  - ✅ AI Agent 可通过阅读示例学习命令调用风格
  - ✅ 五阶段模板强制结构化输出
  - ✅ 为 TASK-032 (Planner 增强) 提供输出格式参考

---

## ADR-018: 结构化 JSON 工具清单 (TASK-030)

- **Date**: 2026-06-11
- **Status**: Accepted
- **Context**: AI Agent 需要机器可读的全量命令 schema，而非仅 Markdown 文档。工程化方案明确要求结构化 JSON 工具清单。
- **Decision**: 生成 `docs/TOOL_SCHEMA.json`，包含 17 命令组、185 命令、26 错误码、31 个 GUI→CLI 映射。每个命令包含：功能描述、参数列表、返回值、使用示例。
- **Format**: 采用 `FreeCAD_CLI_Toolkit` 根对象，包含 `command_groups`、`error_codes`、`gui_to_cli_mapping`、`execution_rules`、`global_options`、`response_format` 六个顶级字段。
- **Consequences**:
  - ✅ AI Agent 可通过读取单个 JSON 文件发现所有 185 个命令
  - ✅ GUI→CLI 映射表让 AI 从自然语言意图直接映射到命令
  - ✅ 错误码表让 AI 自动选择恢复策略
  - ✅ 为 TASK-031 (Few-shot 示例库) 和 TASK-032 (五阶段执行流) 奠定基础

---

## ADR-017: E2E Agent 测试 Bug 修复 (TASK-028)

- **Date**: 2026-06-11
- **Status**: Accepted
- **Context**: E2E Agent 测试发现 5 个 bug，其中 2 个 P0 阻塞所有 CLI 执行。
- **修复清单**:
  1. **P0 — `--json` 标志位置**: planner.py 中 `--json` 放在子命令末尾，Click 要求全局选项在前。修复：移到 args 开头。
  2. **P0 — `fc` 命令冲突**: Windows 中 `fc` 是内置命令 (file compare)。修复：agent_cmd.py 中用 `shutil.which("fc")` 解析正确路径。
  3. **P1 — Unicode 编码**: Windows GBK 控制台无法输出 Unicode 字符。修复：全部替换为 ASCII 等价物。
  4. **P1 — TaskStatus 枚举**: executor.py 设置字符串而非枚举值。修复：统一用 `TaskStatus.SUCCESS` 等。
  5. **P1 — 会话持久化**: 多 subprocess 调用间文档状态丢失。修复：planner 注入 `--project` 参数。
- **Consequences**:
  - ✅ `fc agent` 完整流程可执行
  - ✅ 28 E2E 测试全部通过
  - ✅ 零回归 (212 runtime + 347 core 测试通过)

---

## ADR-016: Test Coverage Strategy

- **Date**: 2026-06-10
- **Status**: Accepted
- **Context**: 项目测试分布严重不均。需要三层测试策略覆盖所有代码路径。
- **Decision**: 采用三层测试策略：
  1. **MockBackend 单元测试** — 不需要 FreeCAD，CI 可运行，覆盖所有命令/工具
  2. **集成测试** — 需要真实 FreeCAD，使用 pytest.mark.skipif 跳过
  3. **E2E 测试** — fc agent 端到端，需 FreeCAD + 时间
- **Consequences**:
  - ✅ MockBackend 测试可在任何环境运行（无 FreeCAD 依赖）
  - ✅ 集成测试自动跳过，不阻塞 CI
  - ✅ 从 251 tests 增长到 1,367 tests（+445%）

---

## ADR-015: Backend Geometry Deduplication via Mixin Inheritance

- **Date**: 2026-06-10
- **Status**: Accepted
- **Context**: HeadlessBackend 和 RPCBackend 各自实现了 8 个几何操作方法，与 GeometryOpsMixin 完全重复。共 ~300 行重复代码。
- **Decision**: 让两个 Backend 继承 GeometryOpsMixin，删除各自重复的实现。Mixin 通过 `self._backend.execute_code()` 调用后端，Backend 在 `__init__` 中设置 `self._backend = self`。
- **Consequences**:
  - ✅ 消除 ~300 行重复代码
  - ✅ 几何操作逻辑单一来源（GeometryOpsMixin）
  - ✅ 新增几何操作只需在 Mixin 中实现一次
  - ⚠️ Mixin 的 `_backend` 类型注解改为 `object`（避免循环导入）

---

## ADR-014: HeadlessBackend 批量执行模式

- **Date**: 2026-06-10
- **Status**: Accepted
- **Context**: HeadlessBackend 每次 _execute_macro() 都 subprocess.run() 启动新 FreeCADCmd 进程。多步工作流（创建文档→添加对象→导出）中前一步状态在下一步丢失。
- **Decision**: 添加 batch_start() / batch_add() / batch_execute() 方法。多个操作累积到一个 Python 脚本中，用一次进程调用完成。原有单操作接口保持不变（向后兼容）。
- **方案**: batch_execute() 构建合并脚本，每个操作带独立标记（`___FC_RESULT_N___`），stdout 解析返回 list[dict]。
- **替代方案对比**:
  - 持久进程模式（FreeCADCmd -c 交互模式）：需处理 stdin/pipe 稳定性，跨平台复杂度高
  - 文档序列化（每步保存/重新加载）：性能差，IO 密集
  - **单脚本累积模式（选用）**：简单可靠，无额外依赖，一次调用完成多步操作
- **Consequences**:
  - ✅ 多步工作流状态一致
  - ✅ 进程启动次数从 N 降到 1
  - ✅ 向后兼容，现有代码无需修改
  - ⚠️ batch 内异常不自动回滚（需调用方检查每步结果）

---

## ADR-013: Agent Team Architecture (7 Agents)

- **Date**: 2026-06-10
- **Status**: Accepted
- **Context**: 项目需要多 Agent 协作提高并行效率。
- **Decision**: 使用 6 个专用 Agent + Chief Architect 监督的架构。
- **Agent 列表**:
  - **Chief Architect** (opus) — 架构设计、任务分配、文档维护、验收
  - **fc-core-agent** — BackendInterface, 类型, 几何, IO
  - **fc-cli-agent** — Click 命令组 (17组), OutputManager, plugins, REPL
  - **fc-mcp-agent** — MCP 工具 (6模块~50工具), FastMCP 服务器
  - **fc-runtime-agent** — Planner, Executor, Corrector, BOM
  - **fc-test-agent** — 单元测试, 集成测试, E2E
  - **fc-review-agent** — 架构审查, 安全审查, 接口一致性
- **Consequences**:
  - (+) 专业化：每个 Agent 只需掌握一个领域的上下文
  - (+) 并行：独立任务可同时执行
  - (+) 审查独立：review-agent 确保客观性
  - (-) 通信开销：Agent 间需要同步
  - (-) 需要 Chief Architect 协调避免冲突

---

## ADR-012: Pattern-Matching Planner (No LLM)

- **Date**: 2026-06-10
- **Status**: Accepted (for V1)
- **Context**: The Planner needs to convert natural language to task trees. Using an LLM would add latency and cost.
- **Decision**: Use regex-based pattern matching with keyword templates for V1. LLM-based planning can be added later as an optional backend.
- **Consequences**:
  - (+) Zero latency, zero cost
  - (+) Deterministic, testable
  - (-) Limited to known patterns (12+ templates)
  - (-) Cannot handle truly novel designs
- **Future**: Add `fc agent --llm` flag for LLM-based planning when needed

---

## ADR-011: Subprocess-per-Operation for HeadlessBackend

- **Date**: 2026-06-10
- **Status**: Accepted (with known trade-off)
- **Context**: HeadlessBackend spawns a new FreeCADCmd process for each operation. This is simple but has ~1-3s overhead per call.
- **Decision**: Keep subprocess-per-operation for V1. Optimize later with connection pooling or persistent process.
- **Consequences**:
  - (+) Simple, reliable, stateless
  - (+) Works with any FreeCAD installation
  - (-) ~1-3s overhead per operation
  - (-) No shared state between calls (each macro creates a new document)
- **Mitigation**: For batch operations, use `execute` command to run multiple operations in a single script, or use batch_* mode

---

## ADR-010: ToolResponse Standard Format

- **Date**: 2026-06-09
- **Status**: Accepted
- **Context**: All operations need a consistent response format for AI agent consumption.
- **Decision**: ToolResponse with status, operation, data, message, error_code, suggestion.
- **Consequences**:
  - (+) Uniform error handling
  - (+) AI agents can parse any response
  - (+) Suggestions help users recover

---

## ADR-009: Temp File Cleanup

- **Date**: 2026-06-09
- **Status**: Accepted
- **Context**: HeadlessBackend creates temp .py files for each operation.
- **Decision**: Always clean up temp files in `finally` block.
- **Consequences**:
  - (+) No disk pollution
  - (-) Slightly more complex error handling

---

## ADR-008: Mixin Pattern for Geometry

- **Date**: 2026-06-09
- **Status**: Accepted
- **Context**: Geometry operations need to be shared between CLI commands and backend.
- **Decision**: Use mixin classes (PrimitivesMixin, GeometryOpsMixin) for geometry operations.
- **Consequences**:
  - (+) Code reuse
  - (+) Separation of concerns
  - (-) Mixins need `_backend` attribute (ADR-015 resolves duplication)

---

## ADR-007: Structured JSON Output

- **Date**: 2026-06-09
- **Status**: Accepted
- **Context**: AI agents need machine-readable output.
- **Decision**: All commands support `--json` flag. ToolResponse is the standard format.
- **Consequences**:
  - (+) AI agent friendly
  - (+) Consistent error format
  - (+) Machine-parseable
  - (-) More verbose than plain text

---

## ADR-006: Monorepo with uv Workspace

- **Date**: 2026-06-09
- **Status**: Accepted
- **Context**: Multiple packages (core, cli, mcp, runtime, test) need coordinated development.
- **Decision**: Monorepo with uv workspace, Hatch build system.
- **Consequences**:
  - (+) Single dependency resolution
  - (+) Cross-package refactoring
  - (+) Unified CI
  - (-) Larger repo

---

## ADR-005: FastMCP for MCP Server

- **Date**: 2026-06-09
- **Status**: Accepted
- **Context**: Need MCP server compatible with Claude Desktop, Cursor, etc.
- **Decision**: Use FastMCP (official MCP Python SDK).
- **Consequences**:
  - (+) Official MCP support
  - (+) Decorator-based tool registration
  - (+) Lifespan management
  - (-) Tied to MCP ecosystem

---

## ADR-004: Click for CLI Framework

- **Date**: 2026-06-09
- **Status**: Accepted
- **Context**: Need a robust CLI framework with good help text, nesting, and validation.
- **Decision**: Use Click for all CLI commands.
- **Consequences**:
  - (+) Mature, well-documented
  - (+) Nested command groups
  - (+) Automatic help generation
  - (-) Callback-based (not async)

---

## ADR-003: Macro-Based Headless Execution

- **Date**: 2026-06-09
- **Status**: Accepted
- **Context**: FreeCADCmd can execute Python scripts. No direct C++ API access.
- **Decision**: Write temp .py files, execute via FreeCADCmd subprocess, parse JSON from stdout.
- **Consequences**:
  - (+) Works with any FreeCAD installation
  - (+) No compilation needed
  - (-) Subprocess overhead per operation
  - (-) No shared state between calls

---

## ADR-002: Dual Backend Architecture

- **Date**: 2026-06-09
- **Status**: Accepted
- **Context**: Some users need headless operation (CI/CD), others need GUI interaction.
- **Decision**: Two backends (HeadlessBackend + RPCBackend) implementing BackendInterface.
- **Consequences**:
  - (+) Covers all use cases
  - (+) Backend-agnostic commands
  - (-) Two code paths to maintain (mitigated by ADR-015)

---

## ADR-001: Python as Sole Language

- **Date**: 2026-06-09
- **Status**: Accepted
- **Context**: FreeCAD's primary API is Python. Using Python ensures maximum compatibility.
- **Decision**: Use Python 3.12+ exclusively. No C++, no Rust, no TypeScript.
- **Consequences**:
  - (+) Direct FreeCAD API access
  - (+) Single language for all packages
  - (-) Slower than compiled languages for some operations
