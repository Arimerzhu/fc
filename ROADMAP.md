# ROADMAP.md — fc Development Roadmap

> Single Source of Truth for milestones and timeline.
> Chief Architect 维护。

## Milestones

### M1 — Foundation ✅ COMPLETED (2026-06-09)
**Goal**: Core types, backend abstraction, basic CLI
- [x] Project scaffolding (monorepo, pyproject.toml)
- [x] Core types (Vec3, Placement, ToolResponse, enums)
- [x] BackendInterface ABC
- [x] HeadlessBackend (macro-based FreeCADCmd execution)
- [x] RPCBackend (XML-RPC to FreeCAD GUI)
- [x] Geometry primitives mixin
- [x] Geometry operations mixin
- [x] CLI framework (Click, 16 command groups)
- [x] Output manager (JSON + Rich)
- [x] Unit tests for core types (14 tests)
- [x] Architecture documents

### M2 — CLI Complete ✅ COMPLETED (2026-06-10)
**Goal**: 200+ CLI commands covering all workbenches
- [x] Complete part commands (add, remove, list, get, transform, boolean, copy, mirror, scale, fillet-3d, chamfer-3d, loft, sweep, revolve, extrude, info, bounds)
- [x] Mesh commands (import, export, analyze, repair, refine, decimate, boolean, section, list, info)
- [x] Draft commands (line, wire, circle, array, offset, ...)
- [x] Surface commands (loft, sweep, fill, pipe, ...)
- [x] TechDraw commands (page, view, dimension, export)
- [x] Spreadsheet commands (create, read, write, link)
- [x] Material commands (library, assign, custom)
- [x] Assembly commands (constraint, explode, animation)
- [x] FEM commands (analysis, mesh, result)
- [x] CAM commands (job, toolpath, postprocess)
- [x] Body commands (new, pad, pocket, fillet, chamfer, revolution, groove, list, get)
- [x] Sketch commands (new, add-line, add-circle, add-rect, add-arc, add-ellipse, add-polygon, add-bspline, add-slot, add-point, constrain, close, list, get, validate, solve-status)
- [x] Session management (undo/redo/snapshot/restore/history)
- [x] IO modules (export presets, import auto-detect)

### M3 — MCP Complete ✅ COMPLETED (2026-06-10)
**Goal**: Full MCP tool ecosystem
- [x] 6 tool modules with @mcp.tool() decorated functions (~50 tools)
- [x] Tool schemas matching CLI capabilities
- [x] Error handling via ToolResponse
- [x] FastMCP server with lifespan management

### M4 — Agent Runtime ✅ COMPLETED (2026-06-10)
**Goal**: `fc agent` command for autonomous CAD design
- [x] Planner: Natural language → task tree (12+ templates, dimension extraction, Chinese+English)
- [x] Executor: Task tree → CLI calls (dependency-aware, progress tracking)
- [x] Corrector: Error detection and self-correction (6 error patterns)
- [x] BOM generator: Extract parts list (JSON/CSV/Markdown/Table export)
- [x] `fc agent` CLI command registered
- [x] 212 runtime tests passing

### M5 — Integration & Testing ✅ COMPLETED (2026-06-11)
**Goal**: Verify everything works with real FreeCAD
- [x] Install FreeCAD 1.1.1 and run end-to-end test — 25 integration tests ALL PASSED
- [x] CLI command tests — 17/17 groups, 540 tests passing
- [x] MCP tool tests — 6/6 modules, 268 tests passing
- [x] Integration test framework (8 tests, FreeCAD skip markers)
- [x] RPCBackend.export() P0 bug fixed
- [x] Backend deduplication via GeometryOpsMixin
- [x] Corrector/BOM extended tests — 45 edge case tests
- [x] _build_wrapper_script indentation P0 fix
- [x] Runtime test failures fixed — 14/14 pre-existing failures resolved
- [x] E2E Agent tests — 28 tests ALL PASSED
- [x] 5 E2E bugs fixed (json flag, Unicode, status enum, fc path, session)
- [x] 3 source code bugs fixed (surface, spreadsheet, material)

**Total tests: 1,367 passed**

### M6 — Polish & Production 🟡 70% COMPLETE
**Goal**: Production-ready release
- [x] Plugin system implementation — `plugins.py` (discover/load/register)
- [x] REPL mode for interactive sessions — `commands/repl.py`
- [x] SKILL.md files for AI agent integration — 12 command-group SKILL files
- [x] E2E agent tests — 28 tests, `fc agent` full pipeline verified
- [x] HeadlessBackend batch mode — batch_start/add/execute
- [x] Security fixes — snapshot path traversal, ToolResponse format
- [ ] Performance benchmark (measure subprocess overhead)
- [ ] Path traversal hardening (P2 fix)
- [ ] E2E tests with real FreeCAD in CI (Docker or self-hosted runner)
- [ ] Documentation site (MkDocs or similar)

### M7 — AI Engineering Excellence ✅ 100% COMPLETE
**Goal**: 让 AI Agent 达到工程师级别的运用能力（参考工程化方案）
- [x] 结构化 JSON 工具清单 — 机器可读的全量命令 schema (TASK-030 ✅)
- [x] GUI→CLI 映射表 — 自然语言意图到命令的映射 (TASK-030 ✅)
- [x] Few-shot 示例库 — 5 个从简单到复杂的完整示例 (TASK-031 ✅)
- [x] 五阶段执行流提示词模板 — 强制 AI 按流程执行 (TASK-032 ✅)
- [x] 命令历史上下文注入机制 — 执行结果反馈给 AI (TASK-035 ✅)
- [x] 错误闭环自动学习 — 常见错误自动加入禁止规则 (TASK-036 ✅)
- [x] Function calling schema — 每个 CLI 命令的函数调用定义 (TASK-037 ✅)

### M8 — V1.0 Release 🔲 PLANNED
**Goal**: 正式发布
- [ ] Performance benchmark + optimization
- [ ] Documentation site (MkDocs)
- [ ] CI/CD with FreeCAD integration tests
- [ ] Community templates library
- [ ] Video tutorials

## Version Targets

| Version | Target Date | Deliverables | Status |
|---------|------------|-------------|--------|
| MVP | 2026-06 | `fc part add box` works with real FreeCAD | ✅ Complete |
| V0.5 | 2026-06 | Full CLI (200+ commands, 17 groups) | ✅ Complete |
| V1.0 | 2026-07 | Complete MCP + Agent Runtime + Integration tests | 🟡 95% |
| V1.1 | 2026-07 | AI Engineering complete (M7) — all 7 measures | ✅ Complete |
| V2.0 | 2026-09 | `fc agent` fully autonomous for complex designs | 🟡 90% |
