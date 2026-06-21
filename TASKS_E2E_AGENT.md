# TASK-028: E2E Agent 测试 — `fc agent` 端到端验证

> Single Source of Truth for E2E agent test task.

## Task Specification

| Field | Value |
|-------|-------|
| **ID** | TASK-028 |
| **Goal** | 验证 `fc agent "design a box"` 端到端工作流：Planner → Executor → Corrector → BOM → Export |
| **Priority** | P0 |
| **Status** | 🔲 In Progress |
| **Dependencies** | TASK-009 (FreeCAD integration), TASK-010 (CLI tests), TASK-015 (batch mode) |
| **Assigned Agent** | fc-test-agent |
| **Reviewer** | fc-review-agent |

## Scope

### In Scope
1. **Planner E2E**: 自然语言 → 任务树（验证维度提取、模板匹配、依赖关系）
2. **Executor E2E**: 任务树 → fc CLI 调用 → FreeCAD 执行（验证 subprocess 调用链）
3. **Corrector E2E**: 错误注入 → 自动修正 → 重试成功
4. **BOM E2E**: 执行完成 → BOM 生成 → JSON/CSV/MD 导出
5. **Full Pipeline**: `fc agent "design a box 20x30x40mm"` → STEP + STL + BOM
6. **中文支持**: `fc agent "设计一个长方体 20x30x40mm"` 完整流程
7. **Dry-run**: `fc agent "design a box" --dry-run` 输出任务树 JSON
8. **错误恢复**: 模拟 FreeCAD 未安装 → Corrector 提供安装指导

### Out of Scope
- LLM-based planning (V2.0+)
- Complex assemblies (gear reducer, etc.)
- Performance optimization
- GUI/RPC backend testing

## Deliverables

### D1: E2E Test File
**Path**: `packages/core/tests/test_e2e_agent.py`

Test cases:
```
class TestAgentE2E:
    test_planner_box_dimensions          # "box 20x30x40" → 3 tasks (doc + part + export)
    test_planner_cylinder_chinese        # "设计一个圆柱" → correct template match
    test_planner_no_dimensions           # "design a box" → default 10x10x10
    test_planner_multiple_parts          # "box and cylinder" → 2 part tasks
    test_planner_with_operations         # "box with fillet" → part + fillet tasks
    test_planner_export_formats          # "export to step and stl" → export tasks

class TestExecutorE2E:
    test_execute_simple_box              # plan → fc calls → success
    test_execute_with_retries            # inject failure → corrector → retry → success
    test_execute_dry_run                 # no actual execution, returns plan
    test_execute_export_files            # verify output files exist (.step, .stl, .fcstd)

class TestCorrectorE2E:
    test_corrector_freecad_not_found     # → install guidance
    test_corrector_file_exists           # → add --overwrite
    test_corrector_invalid_parameter     # → clamp to valid range
    test_corrector_max_retries_exceeded  # → graceful failure

class TestBOMGeneratorE2E:
    test_bom_from_plan                   # plan → BOM with correct items
    test_bom_export_json                 # BOM → .json file
    test_bom_export_csv                  # BOM → .csv file
    test_bom_export_markdown             # BOM → .md file

class TestFullPipeline:
    test_fc_agent_box_english            # fc agent "design a box 20x30x40mm"
    test_fc_agent_box_chinese            # fc agent "设计一个长方体 20x30x40mm"
    test_fc_agent_dry_run                # fc agent "design a box" --dry-run
    test_fc_agent_with_exports           # fc agent "box" --export step --export stl
    test_fc_agent_output_dir             # fc agent "box" -o ./test_output
```

### D2: Test Report
**Path**: `E2E_AGENT_TEST_REPORT.md`

Format:
```markdown
# E2E Agent Test Report

## Summary
- Total: N tests
- Passed: N
- Failed: N
- Skipped: N (if FreeCAD not available)

## Test Results
| Test | Status | Duration | Notes |
|------|--------|----------|-------|
| test_planner_box_dimensions | ✅ PASS | 0.05s | ... |

## Timing Breakdown
| Phase | Avg Time | Notes |
|-------|----------|-------|
| Planner | ~0.01s | Regex-based, fast |
| Executor (per task) | ~2-5s | Subprocess overhead |
| Corrector | ~0.01s | Pattern matching |
| BOM | ~0.01s | In-memory |

## Issues Found
- [ ] Issue 1: ...
```

### D3: Fix any discovered bugs
- Document all found bugs in DECISIONS.md or as new TASK items
- Fix P0/P1 bugs immediately
- Defer P2 to future tasks

## Acceptance Criteria

1. **All E2E tests pass** with real FreeCAD 1.1.1 installed
2. **Full pipeline works**: `fc agent "design a box 20x30x40mm"` produces:
   - `output.fcStd` file
   - `output.step` file
   - `output.stl` file
   - `BOM.json`, `BOM.csv`, `BOM.md` files
   - `plan_report.json` file
3. **Dry-run works**: `fc agent "design a box" --dry-run` outputs valid JSON plan
4. **Chinese support works**: `fc agent "设计一个长方体"` produces correct plan
5. **Error recovery works**: Simulated failures are corrected automatically
6. **Test report generated**: `E2E_AGENT_TEST_REPORT.md` with timing data

## Environment Requirements

- FreeCAD 1.1.1 (already installed at `C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe`)
- `fc` CLI (already installed at `/e/Scripts/fc.exe`)
- Python 3.12+
- pytest

## Execution Plan

### Phase 1: Planner E2E Tests (~30 min)
- Test dimension extraction (10 patterns)
- Test template matching (all 12 templates)
- Test dependency tracking
- Test Chinese + English support

### Phase 2: Executor E2E Tests (~30 min)
- Test subprocess execution via fc CLI
- Test dry-run mode
- Test output file generation
- Test timeout handling

### Phase 3: Corrector E2E Tests (~20 min)
- Test all 6 error pattern corrections
- Test retry mechanism
- Test max retries exceeded

### Phase 4: BOM + Full Pipeline (~20 min)
- Test BOM generation from plan
- Test multi-format export
- Test complete `fc agent` command

### Phase 5: Report + Fix (~10 min)
- Generate test report
- Fix any P0/P1 bugs found
- Update architecture documents

## Risks

| Risk | Mitigation |
|------|-----------|
| `fc` command shadowed by bash built-in | Use `fc.exe` full path or `python -m fc_cli` |
| FreeCAD subprocess slow (~2-5s per call) | Use batch mode for multi-step workflows |
| Windows path issues | Use raw strings and `pathlib.Path` |
| Planner regex misses edge cases | Add fallback to default box |
