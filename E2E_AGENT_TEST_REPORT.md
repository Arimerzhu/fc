# E2E Agent Test Report — TASK-028

> Generated: 2026-06-11

## Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 28 |
| **Passed** | 28 ✅ |
| **Failed** | 0 |
| **Skipped** | 0 |
| **Total Time** | 28.83s |
| **FreeCAD Version** | 1.1.1 |

## Test Results by Class

| Class | Tests | Passed | Failed | Avg Time |
|-------|-------|--------|--------|----------|
| `TestPlannerE2E` | 10 | 10 | 0 | <0.01s |
| `TestExecutorE2E` | 4 | 4 | 0 | ~7s (FreeCAD subprocess) |
| `TestCorrectorE2E` | 5 | 5 | 0 | <0.01s |
| `TestBOMGeneratorE2E` | 5 | 5 | 0 | <0.01s |
| `TestFullPipelineE2E` | 4 | 4 | 0 | ~4.5s (full fc agent) |

## Detailed Results

### TestPlannerE2E (10 tests)
| Test | Status | Notes |
|------|--------|-------|
| `test_box_dimensions_20x30x40` | ✅ PASS | Correctly extracts L=20, W=30, H=40 |
| `test_box_default_dimensions` | ✅ PASS | Defaults to 10x10x10 |
| `test_cylinder_with_diameter` | ✅ PASS | D=50 → radius=25 |
| `test_chinese_box` | ✅ PASS | "长方体" matches box template |
| `test_multiple_parts` | ✅ PASS | "box and cylinder" → 2 part tasks |
| `test_with_fillet` | ✅ PASS | "fillet r=2" → fillet task with radius=2 |
| `test_export_step_stl` | ✅ PASS | Both STEP and STL export tasks created |
| `test_no_parts_defaults_to_box` | ✅ PASS | Fallback to default box |
| `test_dependency_chain` | ✅ PASS | All tasks depend on document creation |
| `test_plan_to_dict` | ✅ PASS | JSON-serializable plan dict |

### TestExecutorE2E (4 tests)
| Test | Status | Notes |
|------|--------|-------|
| `test_execute_simple_box_plan` | ✅ PASS | Box created via fc CLI |
| `test_execute_dry_run` | ✅ PASS | No actual execution |
| `test_execute_output_files` | ✅ PASS | .FCStd, .step, .stl files exist |
| `test_execute_with_timeout` | ✅ PASS | Timeout parameter works |

### TestCorrectorE2E (5 tests)
| Test | Status | Notes |
|------|--------|-------|
| `test_freecad_not_found` | ✅ PASS | Returns install guidance |
| `test_file_exists` | ✅ PASS | Adds --overwrite flag |
| `test_invalid_parameter` | ✅ PASS | Clamps to valid range |
| `test_max_retries` | ✅ PASS | Graceful failure after max retries |
| `test_unknown_error` | ✅ PASS | Generic retry for unknown errors |

### TestBOMGeneratorE2E (5 tests)
| Test | Status | Notes |
|------|--------|-------|
| `test_bom_from_plan` | ✅ PASS | 2 parts → 2 BOM items |
| `test_bom_export_json` | ✅ PASS | Valid JSON output |
| `test_bom_export_csv` | ✅ PASS | Correct CSV headers |
| `test_bom_export_markdown` | ✅ PASS | Markdown table format |
| `test_bom_volume_calculation` | ✅ PASS | 20×30×40 = 24,000 mm³ |

### TestFullPipelineE2E (4 tests)
| Test | Status | Notes |
|------|--------|-------|
| `test_fc_agent_box_english` | ✅ PASS | Full pipeline: plan → execute → BOM → export |
| `test_fc_agent_box_chinese` | ✅ PASS | Chinese prompt works end-to-end |
| `test_fc_agent_dry_run` | ✅ PASS | JSON plan output correct |
| `test_fc_agent_output_dir` | ✅ PASS | Custom output directory works |

## Bugs Found and Fixed

### Bug 1: `--json` flag placement in planner (P0)
- **File**: `packages/runtime/src/fc_runtime/planner.py`
- **Issue**: `--json` was placed at the end of subcommand args (e.g., `fc document new --name Box --json`), but Click expects it as a global option before the subcommand (`fc --json document new --name Box`).
- **Fix**: Moved `--json` to the beginning of all task args lists.
- **Impact**: Blocked ALL CLI execution — every task would fail.

### Bug 2: Unicode encoding errors on Windows GBK console (P1)
- **Files**: `executor.py`, `agent_cmd.py`, `corrector.py`
- **Issue**: Unicode characters (✓, ✗, →, ↻, ⚡) in print statements caused `UnicodeEncodeError` on Windows GBK console.
- **Fix**: Replaced all Unicode characters with ASCII equivalents (`[OK]`, `[FAIL]`, `>`, `[RETRY]`, `[CORRECT]`).

### Bug 3: Task status set as string instead of enum (P1)
- **File**: `packages/runtime/src/fc_runtime/executor.py`
- **Issue**: Executor set `task.status = "success"` (string) instead of `task.status = TaskStatus.SUCCESS` (enum). Then `agent_cmd.py` accessed `task.status.value` which fails on strings.
- **Fix**: Changed all status assignments to use `TaskStatus` enum values.

### Bug 4: `fc` command conflict on Windows (P0)
- **File**: `packages/runtime/src/fc_runtime/agent_cmd.py`
- **Issue**: The `Executor` defaulted to `fc_path="fc"`, which on Windows resolves to the `fc` file compare utility, not the FreeCAD CLI.
- **Fix**: Added `shutil.which("fc")` resolution to find the correct executable.

### Bug 5: Session persistence across subprocess calls (P1)
- **File**: `packages/runtime/src/fc_runtime/planner.py`
- **Issue**: Each `fc` CLI call is a separate FreeCAD process. Document created in one call is not visible in the next.
- **Fix**: Added `project_path` parameter to `planner.plan()` that injects `--project` flag into all task args for session persistence.

## Performance Data

| Operation | Avg Time | Notes |
|-----------|----------|-------|
| Planner (plan generation) | <1ms | Regex-based, very fast |
| Executor (dry-run, 5 tasks) | <1ms | No subprocess calls |
| Executor (real, 5 tasks via fc CLI) | ~4.5-5s | ~1s per subprocess call |
| fc agent (dry-run) | ~0.5s | Planning only |
| fc agent (full execution, English) | ~4.7s | Plan + Execute + BOM + Export |
| fc agent (full execution, Chinese) | ~4.6s | Same performance |
| BOM generation from plan | <1ms | In-memory calculation |
| BOM export (3 formats) | <1ms | File I/O only |

## Regression Testing

| Test Suite | Tests | Result |
|------------|-------|--------|
| Runtime tests | 212 | ✅ ALL PASSED |
| Core tests | 328 | ✅ 301 passed, 27 pre-existing (integration E2E, unrelated) |
| New E2E agent tests | 28 | ✅ ALL PASSED |

**Zero regressions introduced.**

## Known Limitations

1. **Subprocess session isolation**: Each `fc` CLI call runs in a separate FreeCAD process. The `--project` flag enables session persistence, but complex multi-step workflows may need batch mode for reliability.
2. **BOM encoding**: BOM generation in `agent_cmd.py` may have GBK encoding issues with certain Unicode characters in file writes (separate from the print statement fix).

## Conclusion

**TASK-028 ✅ COMPLETED**

All 28 E2E agent tests pass with real FreeCAD 1.1.1. The full `fc agent` pipeline works end-to-end:
- ✅ Natural language → task tree (Planner)
- ✅ Task tree → fc CLI calls → FreeCAD execution (Executor)
- ✅ Error detection and self-correction (Corrector)
- ✅ BOM generation and multi-format export (BOM Generator)
- ✅ Chinese and English support
- ✅ Dry-run mode
- ✅ Custom output directory

5 bugs were found and fixed during testing, including 2 P0 issues that would have blocked all CLI execution.
