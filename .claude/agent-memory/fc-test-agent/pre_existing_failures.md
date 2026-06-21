---
name: pre-existing-test-failures
description: 31 pre-existing test failures in test_runtime.py and test_integration_e2e.py that are NOT caused by new tests
metadata:
  type: project
---

As of 2026-06-10, 31 tests fail in the existing test suite. These are pre-existing bugs, not caused by new test additions:

**test_runtime.py failures (13):**
- Several `TestPlannerEnhancements` tests fail because the Planner doesn't extract dimensions/params correctly for some Chinese inputs
- `TestBOMGeneration.test_bom_from_plan_with_box/cylinder` fail because `from_plan()` checks `task_status == "success"` but dry_run sets status differently
- `TestBOMGeneration.test_bom_export_json/test_bom_json_roundtrip` fail with `NameError: name 'json' is not defined` (missing import at module level in the test file)
- `TestFullWorkflow.test_full_workflow_box/cylinder` fail due to Planner not extracting correct dimensions
- `TestCorrectorPatterns.test_object_not_found_error` fails (pattern ordering issue)
- `TestCorrectorPatterns.test_file_exists_no_duplicate_overwrite` fails (NoneType error)

**test_integration_e2e.py failures (18):**
- All require real FreeCAD but are not properly skipped — they use `os.environ.setdefault("FREECAD_PATH", ...)` pointing to a specific Windows path

**How to apply:** These failures should be tracked separately. New tests should not depend on or assert against these broken behaviors.
