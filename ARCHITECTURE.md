# ARCHITECTURE.md — fc System Architecture

> Single Source of Truth for architectural decisions and system design.
> Chief Architect 维护。任何架构变更必须先更新此文件。

## 1. Dual Backend Architecture

### 1.1 Design

All FreeCAD operations go through `BackendInterface`, an abstract base class.
Two concrete implementations exist:

| Backend | Class | Use Case |
|---------|-------|----------|
| Headless | `HeadlessBackend` | CI/CD, batch processing, no GUI |
| RPC | `RPCBackend` | Interactive, screenshots, real-time |

### 1.2 HeadlessBackend

- Executes Python scripts via `FreeCADCmd` subprocess
- Each operation writes a temp `.py` macro file
- Macro is wrapped with imports and `___FC_RESULT___:` JSON marker
- Result parsed from stdout
- Temp files cleaned up after execution (in `finally` block)
- **Batch mode**: `batch_start() / batch_add() / batch_execute()` for multi-step workflows in a single process

### 1.3 RPCBackend

- Connects to FreeCAD GUI via XML-RPC
- Requires FreeCAD MCP addon running
- Uses `_TimeoutTransport` for configurable socket timeout
- All methods forwarded via `_call()`

### 1.4 Backend Selection

```bash
fc --backend headless ...    # Default
fc --backend rpc --host localhost --port 9875
```

## 2. Type System

All types in `fc_core/types.py`:

| Type | Description |
|------|-------------|
| `Vec3` | 3D vector, parseable from "x,y,z" |
| `Placement` | Position + rotation axis + angle |
| `Color` | RGBA (0.0-1.0) |
| `BoundingBox` | 3D bounds with dimensions property |
| `DocumentInfo` | Document metadata |
| `ObjectInfo` | Object metadata |
| `ToolResponse` | Standard response: status, operation, data, message, error_code, suggestion |
| `Units` | mm, cm, m, in, ft |
| `ExportFormat` | step, stl, obj, brep, dxf, svg, gltf, 3mf, pdf, fcstd, ... |
| `ImportFormat` | step, stl, obj, dxf, brep, ... |

### ToolResponse Format

```json
{
  "status": "ok",
  "operation": "object_create",
  "data": {"name": "Box", "type_id": "Part::Box"},
  "message": "Created Part::Box: Box"
}
```

Error format:
```json
{
  "status": "error",
  "operation": "object_create",
  "error": {"code": "CREATE_FAILED", "message": "...", "suggestion": "..."}
}
```

## 3. Geometry System

### 3.1 Primitives (PrimitivesMixin)

| Method | FreeCAD Type | Parameters |
|--------|-------------|------------|
| `add_box` | `Part::Box` | length, width, height |
| `add_cylinder` | `Part::Cylinder` | radius, height |
| `add_sphere` | `Part::Sphere` | radius |
| `add_cone` | `Part::Cone` | radius1, radius2, height |
| `add_torus` | `Part::Torus` | radius1, radius2 |
| `add_wedge` | `Part::Wedge` | xmin/ymin/zmin/xmax/ymax/zmax |
| `add_helix` | `Part::Helix` | pitch, height, radius |

### 3.2 Operations (GeometryOpsMixin)

| Method | FreeCAD Type | Description |
|--------|-------------|-------------|
| `boolean_union` | `Part::MultiFuse` | Fuse two objects |
| `boolean_cut` | `Part::Cut` | Subtract tool from base |
| `boolean_common` | `Part::MultiCommon` | Intersection |
| `fillet_edges` | `Part::Feature` | Fillet selected/all edges |
| `chamfer_edges` | `Part::Feature` | Chamfer selected/all edges |
| `mirror_object` | `Part::Feature` | Mirror across XY/XZ/YZ |
| `scale_object` | `Part::Feature` | Uniform or non-uniform scale |
| `transform_placement` | — | Set position/rotation |

### 3.3 Geometry Deduplication (ADR-015)

Both `HeadlessBackend` and `RPCBackend` inherit `GeometryOpsMixin`. Mixin operations call `self._backend.execute_code()`. Backends set `self._backend = self` in `__init__`. This eliminates ~300 lines of duplicated code.

## 4. CLI Architecture

### 4.1 Command Groups (17 groups, ~200+ commands)

| Group | File | Key Commands | Description |
|-------|------|-------------|-------------|
| `document` | `document.py` | new, open, save, info, close, list | Document management |
| `part` | `part.py` | add, remove, list, get, transform, boolean, copy, mirror, scale, fillet-3d, chamfer-3d, loft, sweep, revolve, extrude, info, bounds, hole | 3D parts |
| `sketch` | `sketch.py` | new, add-line, add-circle, add-rect, add-arc, add-ellipse, add-polygon, add-bspline, add-slot, add-point, constrain, close, list, get, validate, solve-status | 2D sketching |
| `body` | `body.py` | new, pad, pocket, fillet, chamfer, revolution, groove, hole, pattern-linear, pattern-polar, pattern-mirror, shell, draft, datum-plane, datum-point, datum-line, set-tip, remove-feature, list, get | PartDesign |
| `export` | `export.py` | step, stl, obj, brep, dxf, svg, pdf, gltf, 3mf, fcstd, presets | Export formats |
| `import` | `import_cmd.py` | auto, step, stl, obj, dxf, brep, info | Import formats |
| `session` | `session_cmd.py` | undo, redo, status, history, snapshot, restore | Session management |
| `execute` | `execute.py` | code, file | Raw Python execution |
| `mesh` | `mesh.py` | import, export, analyze, repair, refine, decimate, boolean, section, list, info | Mesh operations |
| `draft` | `draft.py` | line, wire, circle, rect, arc, polygon, text, dimension, array, offset, move, rotate, scale, trim, list | Draft workbench |
| `surface` | `surface.py` | loft, sweep, fill, pipe, offset, thicken, flatten, sew, list | Surface operations |
| `techdraw` | `techdraw.py` | page, view, dimension, annotation, symbol, export, list, get | Technical drawings |
| `spreadsheet` | `spreadsheet.py` | create, read, write, link, formula, alias, show, list, clear, export, import | Spreadsheet-driven design |
| `material` | `material.py` | library, assign, create, edit, remove, show, export, import | Material management |
| `assembly` | `assembly.py` | create, add, remove, constraint, solve, explode, animate, list, ground, show | Assembly operations |
| `fem` | `fem.py` | analysis, mesh, material, constraint, solve, result, list | FEM analysis |
| `cam` | `cam.py` | job, tool, toolpath, postprocess, simulate, list, show | CAM operations |

### 4.2 Global Options

| Option | Description |
|--------|-------------|
| `--json` | JSON output for AI agents |
| `--backend` | headless or rpc |
| `--freecad-path` | Override FreeCAD path |
| `--project` | Project file for session persistence |
| `--host` | RPC host |
| `--port` | RPC port |

### 4.3 Output Format

- **Human mode**: Rich tables, colored text, progress indicators
- **JSON mode**: Structured JSON to stdout, errors to stderr

### 4.4 Plugin System

- Drop-in Python packages in `~/.fc/plugins/`
- `plugins.py` handles discover/load/register
- Example: `examples/plugins/hello_plugin.py`

### 4.5 REPL Mode

- `fc repl` starts interactive session
- Commands share backend state within session
- Auto-disconnect on exit

## 5. MCP Architecture

### 5.1 Server

- FastMCP server named "FreeCAD"
- Lifespan management for startup/shutdown
- All tools registered via `@mcp.tool()` decorators

### 5.2 Tool Modules (6 modules, ~50 tools)

| Module | File | Tools | Description |
|--------|------|-------|-------------|
| `document` | `document.py` | create, open, save, close, info, list | Document management |
| `geometry` | `geometry.py` | create primitives (box, cylinder, sphere, cone, torus), boolean, fillet, chamfer, mirror, scale, delete, transform | 3D geometry |
| `sketch` | `sketch.py` | create, add geometry, constrain | 2D sketching |
| `export` | `export.py` | step, stl, obj, brep, dxf, svg, pdf, gltf | Export formats |
| `execute` | `execute.py` | execute_code, execute_file | Raw Python execution |
| `query` | `query.py` | get_object, get_properties, list_objects | Object queries |

## 6. Agent Runtime Architecture

### 6.1 Components

| Component | File | Description |
|-----------|------|-------------|
| **Planner** | `planner.py` | Decomposes natural language into Task tree with dependencies |
| **Executor** | `executor.py` | Runs tasks via CLI subprocess, tracks results |
| **Corrector** | `corrector.py` | Detects errors and proposes fixes (6 error patterns) |
| **BOM Generator** | `bom.py` | Extracts parts list, exports JSON/CSV/Markdown/Table |
| **Agent Command** | `agent_cmd.py` | `fc agent` CLI entry point |

### 6.2 Workflow

```
User: "设计一个二级圆柱齿轮减速器"
  → Planner: Analyze requirements, create task tree (document → parts → operations → exports)
  → Executor: For each task (respecting dependencies), call fc commands
  → Corrector: If step fails, detect error pattern and retry with fix
  → BOM Generator: Extract parts list from plan context
  → Output: STEP + STL + BOM + plan_report.json
```

### 6.3 Planner Features

- **Pattern matching**: 12+ design templates (box, cylinder, flange, gear, shaft, housing, bolt, nut, bearing, reducer, etc.)
- **Dimension extraction**: Parses "10x20x30", "D=50", "长10 宽20 高30", etc.
- **Operation detection**: Boolean, fillet, chamfer, mirror, array
- **Export detection**: Auto-detects requested formats, defaults to STEP+STL
- **Dependency tracking**: Tasks declare dependencies, executor runs in correct order
- **Chinese + English**: Supports both languages

### 6.4 Corrector Features

- **6 error patterns**: no_document, object_not_found, invalid_parameter, file_exists, timeout, syntax_error
- **Auto-fix strategies**: create document, fix object name, clamp parameters, add --overwrite, retry with timeout, fix syntax
- **Max retries**: Configurable (default 3)

## 7. IO Modules

### 7.1 Export (`fc_core/io/export.py`)

- **12 export presets**: 3d_print, 3d_print_fast, cnc, cad_exchange, visualization, etc.
- **Format-specific settings**: Tolerance, angular deflection, binary/ASCII

### 7.2 Import (`fc_core/io/import_mod.py`)

- **Auto-detection**: By file extension and content
- **Format categories**: Mesh (stl, obj, ply, off, 3mf), CAD (step, iges, brep, fcstd), Draft (dxf, svg)

## 8. Security Model

- No network access except RPC (localhost only)
- Temp files cleaned up after use (in `finally` blocks)
- No arbitrary code execution except via explicit `execute` command
- All file paths validated before use
- Snapshot names validated (alphanumeric + hyphen + underscore only)

## 9. Extension Points

- **Plugins**: Drop-in Python packages in `~/.fc/plugins/`
- **Custom commands**: Register via entry points
- **Custom MCP tools**: Register via plugin system
- **Templates**: User-defined document templates
- **Presets**: Export/import format presets

## 10. AI Engineering System (M7)

### 10.1 工程化方案概述

基于《让 AI 熟练运用 FreeCAD CLI 的工程化方案》，建立完整的 AI 工具认知体系：

```
AI 工具认知 → 执行流程 → 约束规则 → 错误闭环
```

### 10.2 五阶段执行流 (TASK-032)

```
阶段1: 工具选型    → 从 TOOL_SCHEMA.json 选出所需命令
阶段2: 任务拆解    → 拆为原子步骤，每步一条 CLI 命令
阶段3: 坐标与依赖  → 计算坐标、标注依赖元素、拓扑关系
阶段4: 依赖校验    → 检查所有依赖合法，无悬空引用
阶段5: 命令输出    → 按顺序输出 CLI 命令 + 注释
```

**规则**: 跳过任何一步都算失败。

### 10.3 结构化工具清单 (TASK-030 ✅)

- `docs/TOOL_SCHEMA.json` — 17 命令组, 185 命令, 26 错误码, 31 GUI 映射
- 每个命令包含：功能、参数、返回值、示例、常见错误
- AI Agent 通过读取此文件自动发现所有命令

### 10.4 Few-shot 示例库 (TASK-031 ✅)

- `docs/examples/01_simple_box_with_hole.md` — 简单：底板通孔
- `docs/examples/02_mounting_bracket.md` — 中等：带凸台倒角安装支架
- `docs/examples/03_simple_assembly.md` — 中等：底座+支柱装配体
- `docs/examples/04_parametric_design.md` — 中等：参数化盒子
- `docs/examples/05_full_workflow.md` — 复杂：从需求到工程图

### 10.5 上下文注入机制 (TASK-035 ✅)

- `executor.py` 新增 `ElementSummary`、`BatchContext` 数据类
- 每批 ≤10 命令执行后，自动生成元素摘要反馈给 AI
- 摘要包含：元素名称、类型、坐标、尺寸、拓扑关系
- 后续任务只能引用已创建的元素（`validate_element_reference()`）
- 协议文档：`docs/CONTEXT_INJECTION_PROTOCOL.md`

### 10.6 错误闭环自动学习 (TASK-036 ✅)

- `error_rules.py` — `ErrorRulesEngine`：错误模式提取、计数、规则生成
- 8 种错误模式识别：`missing_flag`, `invalid_value`, `negative_dimension`, `unknown_object`, `missing_document`, `file_exists`, `wrong_type`, `missing_param`
- 同一错误模式 ≥3 次 → 自动生成 `ForbiddenRule`
- 规则持久化：JSON 导出/导入 + Markdown 文档
- `corrector.py` 集成：`analyze()` 自动记录错误到 rules engine
- 规则文档：`docs/ERROR_RULES.md`（自动维护）

### 10.7 Function Calling Schema (TASK-037 ✅)

- `docs/FUNCTION_SCHEMAS.json` — 185 个 OpenAI function calling 定义
- `scripts/generate_function_schemas.py` — 从 TOOL_SCHEMA.json 自动生成
- 每个函数包含：name、description、parameters (JSON Schema)、required、example
- AI 通过函数调用生成结构化参数，消灭语法/顺序/拼写错误

### 10.8 AI 工程化完成状态

| 任务 | 状态 | 说明 |
|------|------|------|
| 结构化工具清单 | ✅ | TOOL_SCHEMA.json — 17组/185命令 |
| GUI→CLI 映射表 | ✅ | 内嵌于 TOOL_SCHEMA.json |
| Few-shot 示例库 | ✅ | 5 个示例 |
| 五阶段执行流模板 | ✅ | TASK-032 — 完整性校验 + 循环依赖检测 |
| 命令历史上下文注入 | ✅ | TASK-035 — ElementSummary/BatchContext |
| 错误闭环自动学习 | ✅ | TASK-036 — ErrorRulesEngine |
| Function calling schema | ✅ | TASK-037 — 185 function definitions |

## 11. Known Limitations

1. **HeadlessBackend subprocess overhead**: Each operation spawns a new FreeCADCmd process (~1-3s overhead). Mitigated by batch mode.
2. **No shared state between headless calls**: Each macro runs in a fresh FreeCAD instance. Mitigated by batch mode and `--project`.
3. **RPCBackend requires FreeCAD GUI**: Must have FreeCAD running with MCP addon
4. **No async support**: Click is callback-based, not async
5. **No real-time collaboration**: Single-user design
6. **Planner is regex-based**: Limited to known patterns (12+ templates). LLM-based planning planned for future.
7. **AI engineering incomplete**: M7 at 40%. Five-phase execution flow, context injection, error learning loop, and function calling schema pending.

## 11. Package Dependency Graph

```
fc-core (types, backend, geometry, io)
    ↑
    ├── fc-cli (commands, output, plugins, repl)
    │       ↑
    │       └── fc-runtime (planner, executor, corrector, bom)
    │
    └── fc-mcp (server, tools)
```

**Rule**: Dependencies only flow upward. `fc-core` has no dependencies on other fc packages.
