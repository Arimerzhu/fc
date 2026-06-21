# fc-core Integration Test Plan

> **Status**: FreeCAD not available on this system — integration tests cannot be run yet.
> This document defines the full integration test suite to execute once FreeCAD is installed.

## Prerequisites

1. **Install FreeCAD** (https://www.freecad.org/downloads.php)
   - Windows default: `C:\Program Files\FreeCAD*\bin\FreeCADCmd.exe`
   - Ensure `FreeCADCmd` is on PATH or set `FREECAD_PATH` env var
2. **Verify**: `python -c "from fc_core.backend import HeadlessBackend; b = HeadlessBackend(); b.connect(); print(b.get_version())"`
3. **Run**: `python -m pytest packages/core/tests/integration/ -v --tb=short`

---

## Test Environment Setup

```python
# conftest.py for integration tests
import pytest
import tempfile
import os
from fc_core.backend import HeadlessBackend

@pytest.fixture(scope="session")
def backend():
    """Create a shared HeadlessBackend for the test session."""
    b = HeadlessBackend(timeout=120)
    b.connect()
    yield b
    b.disconnect()

@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test artifacts."""
    with tempfile.TemporaryDirectory(prefix="fc_test_") as d:
        yield d

@pytest.fixture
def new_doc(backend):
    """Create a fresh document for each test."""
    backend.document_new("TestDoc")
    yield backend
    try:
        backend.document_close()
    except Exception:
        pass
```

---

## Test Suite 1: Backend Connection & Lifecycle

**File**: `tests/integration/test_backend_lifecycle.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_connect` | Verify backend connects | `b = HeadlessBackend(); b.connect()` | `is_connected() == True` |
| `test_get_version` | Get FreeCAD version | `b.get_version()` | Returns version string like "1.0.0" |
| `test_disconnect` | Clean disconnect | `b.disconnect()` | `is_connected() == False` |
| `test_reconnect` | Connect after disconnect | `b.disconnect(); b.connect()` | `is_connected() == True` |
| `test_find_freecad_env` | FREECAD_PATH env var | Set env var, call `find_freecad()` | Returns path from env |
| `test_find_freecad_not_found` | Missing FreeCAD | Clear PATH, call `find_freecad()` | Raises `FileNotFoundError` with install instructions |
| `test_timeout_config` | Custom timeout | `HeadlessBackend(timeout=300)` | `_timeout == 300` |
| `test_macro_cleanup` | Temp files cleaned | Run any operation, check temp dir | No `fc_macro_*` files left behind |

---

## Test Suite 2: Document Operations

**File**: `tests/integration/test_document.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_document_new` | Create new document | `document_new("TestDoc")` | `status == "ok"`, data.name == "TestDoc" |
| `test_document_new_default` | Default name | `document_new()` | `status == "ok"`, name == "Untitled" |
| `test_document_info` | Get document info | Create doc, `document_info()` | Returns name, label, objects_count == 0 |
| `test_document_save` | Save to FCStd | `document_save(path)` | File exists on disk, `status == "ok"` |
| `test_document_save_no_path` | Save without path | `document_save()` (no prior path) | `status == "error"`, error_code == "NO_PATH" |
| `test_document_open` | Open existing file | Save then `document_open(path)` | `status == "ok"`, objects_count correct |
| `test_document_close` | Close document | `document_close()` | `status == "ok"`, `_current_doc_path is None` |
| `test_document_save_as` | Save As new path | `document_save(new_path)` | New file exists, `_current_doc_path` updated |
| `test_document_open_nonexistent` | Open missing file | `document_open("nonexistent.fcstd")` | `status == "error"`, error_code == "OPEN_FAILED" |

---

## Test Suite 3: Object CRUD Operations

**File**: `tests/integration/test_objects.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_object_create_box` | Create Part::Box | `object_create("Part::Box", "MyBox", {"Length": 20})` | `status == "ok"`, type_id == "Part::Box" |
| `test_object_create_cylinder` | Create Part::Cylinder | `object_create("Part::Cylinder", "MyCyl", {"Radius": 5, "Height": 10})` | `status == "ok"` |
| `test_object_list` | List objects | Create 2 objects, `object_list()` | count == 2, objects array has correct names |
| `test_object_get` | Get object details | Create box, `object_get("MyBox")` | Returns name, type_id, placement, bounding_box, shape |
| `test_object_get_nonexistent` | Get missing object | `object_get("Ghost")` | `status == "error"`, error_code == "GET_FAILED" |
| `test_object_edit` | Edit object properties | Create box, `object_edit("MyBox", {"Length": 50})` | `status == "ok"` |
| `test_object_delete` | Delete object | Create box, `object_delete("MyBox")` | `status == "ok"`, object no longer in list |
| `test_object_delete_nonexistent` | Delete missing object | `object_delete("Ghost")` | `status == "error"`, error_code == "DELETE_FAILED" |
| `test_object_create_sphere` | Create Part::Sphere | `object_create("Part::Sphere", "S1", {"Radius": 10})` | `status == "ok"` |
| `test_object_create_cone` | Create Part::Cone | `object_create("Part::Cone", "C1", {"Radius1": 5, "Radius2": 2, "Height": 10})` | `status == "ok"` |
| `test_object_create_torus` | Create Part::Torus | `object_create("Part::Torus", "T1", {"Radius1": 10, "Radius2": 3})` | `status == "ok"` |
| `test_object_create_helix` | Create Part::Helix | `object_create("Part::Helix", "H1", {"Pitch": 5, "Height": 20})` | `status == "ok"` |

---

## Test Suite 4: Boolean Operations

**File**: `tests/integration/test_boolean.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_boolean_union` | Fuse two boxes | Create Box1, Box2, `boolean_union("Box1", "Box2")` | `status == "ok"`, result is Part::MultiFuse |
| `test_boolean_union_missing_base` | Union with missing base | `boolean_union("Ghost", "Box2")` | `status == "error"` |
| `test_boolean_cut` | Subtract tool from base | Create Box1, Cyl1, `boolean_cut("Box1", "Cyl1")` | `status == "ok"`, result is Part::Cut |
| `test_boolean_cut_missing_tool` | Cut with missing tool | `boolean_cut("Box1", "Ghost")` | `status == "error"` |
| `test_boolean_common` | Intersection of two boxes | Create Box1, Box2, `boolean_common("Box1", "Box2")` | `status == "ok"`, result is Part::MultiCommon |
| `test_boolean_custom_name` | Custom result name | `boolean_union("B1", "B2", result_name="MyFusion")` | Result object named "MyFusion" |

---

## Test Suite 5: Feature Operations

**File**: `tests/integration/test_features.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_fillet_all_edges` | Fillet all edges of box | Create box, `fillet_edges("Box", radius=1.0)` | `status == "ok"`, result is Part::Feature |
| `test_fillet_selected_edges` | Fillet specific edges | Create box, `fillet_edges("Box", radius=1.0, edges=[0,1,2])` | `status == "ok"` |
| `test_fillet_nonexistent` | Fillet missing object | `fillet_edges("Ghost", radius=1.0)` | `status == "error"` |
| `test_chamfer_all_edges` | Chamfer all edges | Create box, `chamfer_edges("Box", size=1.0)` | `status == "ok"` |
| `test_chamfer_selected_edges` | Chamfer specific edges | Create box, `chamfer_edges("Box", size=1.0, edges=[0])` | `status == "ok"` |
| `test_mirror_xy` | Mirror across XY plane | Create box, `mirror_object("Box", plane="XY")` | `status == "ok"` |
| `test_mirror_xz` | Mirror across XZ plane | Create box, `mirror_object("Box", plane="XZ")` | `status == "ok"` |
| `test_mirror_yz` | Mirror across YZ plane | Create box, `mirror_object("Box", plane="YZ")` | `status == "ok"` |
| `test_scale_uniform` | Uniform scale | Create box, `scale_object("Box", factor=2.0)` | `status == "ok"` |
| `test_scale_nonuniform` | Non-uniform scale | Create box, `scale_object("Box", factor=[2.0, 1.0, 0.5])` | `status == "ok"` |

---

## Test Suite 6: Sketch Operations

**File**: `tests/integration/test_sketch.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_sketch_new_xy` | Create sketch on XY plane | `sketch_new(plane="XY")` | `status == "ok"`, type is Sketcher::SketchObject |
| `test_sketch_new_xz` | Create sketch on XZ plane | `sketch_new(plane="XZ")` | `status == "ok"` |
| `test_sketch_new_yz` | Create sketch on YZ plane | `sketch_new(plane="YZ")` | `status == "ok"` |
| `test_sketch_new_custom_name` | Named sketch | `sketch_new(name="MySketch")` | Object named "MySketch" |
| `test_sketch_new_with_offset` | Sketch with offset | `sketch_new(plane="XY", offset=5.0)` | `status == "ok"` |

---

## Test Suite 7: PartDesign Operations

**File**: `tests/integration/test_partdesign.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_body_new` | Create new body | `body_new()` | `status == "ok"`, type is PartDesign::Body |
| `test_body_new_named` | Named body | `body_new(name="MyBody")` | Object named "MyBody" |
| `test_body_pad` | Pad a sketch | Create body + sketch, `body_pad("Body", "Sketch", length=10.0)` | `status == "ok"`, pad created |
| `test_body_pad_symmetric` | Symmetric pad | `body_pad("Body", "Sketch", length=10.0, symmetric=True)` | `status == "ok"` |
| `test_body_pad_missing_body` | Pad with missing body | `body_pad("Ghost", "Sketch")` | `status == "error"` |
| `test_body_pad_missing_sketch` | Pad with missing sketch | `body_pad("Body", "Ghost")` | `status == "error"` |

---

## Test Suite 8: Export Operations

**File**: `tests/integration/test_export.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_export_step` | Export to STEP | Create box, `export("out.step")` | File exists, `status == "ok"`, file_size > 0 |
| `test_export_stl` | Export to STL | Create box, `export("out.stl")` | File exists, `status == "ok"` |
| `test_export_brep` | Export to BREP | Create box, `export("out.brep")` | File exists, `status == "ok"` |
| `test_export_obj` | Export to OBJ | Create box, `export("out.obj")` | File exists, `status == "ok"` |
| `test_export_fcstd` | Export to FCStd | Create box, `export("out.fcstd")` | File exists, `status == "ok"` |
| `test_export_format_detection` | Auto-detect format | `export("out.step")` without fmt param | Correctly detects "step" format |
| `test_export_dxf` | Export to DXF | Create sketch, `export("out.dxf")` | `status == "ok"` (requires importDXF module) |
| `test_export_svg` | Export to SVG | Create sketch, `export("out.svg")` | `status == "ok"` (requires importSVG module) |
| `test_export_iges` | Export to IGES | Create box, `export("out.iges")` | File exists, `status == "ok"` |

---

## Test Suite 9: Geometry Primitives (PrimitivesMixin)

**File**: `tests/integration/test_primitives.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_add_box` | Add box via mixin | `add_box("Box1", 20, 10, 5)` | `status == "ok"`, volume == 1000 |
| `test_add_box_default` | Default box | `add_box()` | `status == "ok"`, 10x10x10 |
| `test_add_box_with_position` | Box at position | `add_box("B1", position=Vec3(10, 20, 30))` | `status == "ok"` |
| `test_add_cylinder` | Add cylinder | `add_cylinder("C1", radius=5, height=10)` | `status == "ok"`, volume ~785.4 |
| `test_add_sphere` | Add sphere | `add_sphere("S1", radius=5)` | `status == "ok"`, volume ~523.6 |
| `test_add_cone` | Add cone | `add_cone("C1", radius1=5, radius2=2, height=10)` | `status == "ok"` |
| `test_add_torus` | Add torus | `add_torus("T1", radius1=10, radius2=2)` | `status == "ok"` |
| `test_add_wedge` | Add wedge | `add_wedge("W1", 0,0,0, 10,10,10)` | `status == "ok"` |
| `test_add_helix` | Add helix | `add_helix("H1", pitch=5, height=20, radius=5)` | `status == "ok"` |

---

## Test Suite 10: Geometry Operations (GeometryOpsMixin)

**File**: `tests/integration/test_geometry_ops.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_boolean_union_mixin` | Union via mixin | `boolean_union("Box1", "Box2")` | `status == "ok"` |
| `test_boolean_cut_mixin` | Cut via mixin | `boolean_cut("Box1", "Cyl1")` | `status == "ok"` |
| `test_boolean_common_mixin` | Common via mixin | `boolean_common("Box1", "Box2")` | `status == "ok"` |
| `test_fillet_mixin` | Fillet via mixin | `fillet_edges("Box1", radius=1.0)` | `status == "ok"` |
| `test_chamfer_mixin` | Chamfer via mixin | `chamfer_edges("Box1", size=1.0)` | `status == "ok"` |
| `test_mirror_mixin` | Mirror via mixin | `mirror_object("Box1", plane="XY")` | `status == "ok"` |
| `test_scale_mixin` | Scale via mixin | `scale_object("Box1", factor=2.0)` | `status == "ok"` |
| `test_transform_placement` | Transform position | `transform_placement("Box1", position=(10,20,30))` | `status == "ok"` |
| `test_transform_rotation` | Transform rotation | `transform_placement("Box1", rotation=(45,0,0))` | `status == "ok"` |

---

## Test Suite 11: IO Module Integration

**File**: `tests/integration/test_io_integration.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_export_preset_3d_print` | 3D print preset | `export_with_preset(b, "out.stl", "3d_print")` | File exists, STL format |
| `test_export_preset_cad_exchange` | CAD exchange preset | `export_with_preset(b, "out.step", "cad_exchange")` | File exists, STEP format |
| `test_export_preset_unknown` | Unknown preset | `export_with_preset(b, "out.stl", "nonexistent")` | `status == "error"`, error_code == "UNKNOWN_PRESET" |
| `test_export_preset_file_exists` | File exists, no overwrite | Export twice without overwrite | Second call: `status == "error"`, error_code == "FILE_EXISTS" |
| `test_export_batch` | Batch export | `export_batch(b, dir, "test", ["step", "stl", "obj"])` | 3 files created, all `status == "ok"` |
| `test_list_presets` | List presets | `list_presets()` | Returns dict of 8 presets |
| `test_import_detect_format` | Format detection | `detect_format("test.step")` | Returns "cad" |
| `test_import_detect_mesh` | Mesh detection | `detect_format("test.stl")` | Returns "mesh" |
| `test_import_detect_unknown` | Unknown format | `detect_format("test.xyz")` | Returns "unknown" |
| `test_import_file_not_found` | Missing file | `import_file(b, "nonexistent.step")` | `status == "error"`, error_code == "FILE_NOT_FOUND" |
| `test_import_step_file` | Import STEP | Create STEP file, `import_file(b, path)` | `status == "ok"` |
| `test_import_stl_file` | Import STL | Create STL file, `import_file(b, path)` | `status == "ok"` |
| `test_import_fcstd_file` | Import FCStd | Create FCStd, `import_file(b, path)` | `status == "ok"` |
| `test_list_supported_formats` | List formats | `list_supported_formats()` | Returns dict with mesh/cad/freecad/draft keys |

---

## Test Suite 12: Raw Code Execution

**File**: `tests/integration/test_execute.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_execute_simple` | Simple Python | `execute_code("print('hello')")` | `status == "ok"` |
| `test_execute_freecad_api` | FreeCAD API access | `execute_code("import FreeCAD; print(FreeCAD.Version())")` | `status == "ok"` |
| `test_execute_create_object` | Create via code | Execute code that creates a Part::Box | `status == "ok"`, object exists |
| `test_execute_syntax_error` | Syntax error handling | `execute_code("def broken(")` | `status == "error"` |
| `test_execute_runtime_error` | Runtime error handling | `execute_code("raise ValueError('test')")` | `status == "error"` |

---

## Test Suite 13: End-to-End Workflows

**File**: `tests/integration/test_e2e_workflows.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_workflow_simple_part` | Design simple part | New doc -> Box -> Fillet -> Export STEP | All steps succeed, STEP file exists |
| `test_workflow_boolean_design` | Boolean design | New doc -> Box1 + Box2 -> Union -> Export STL | All steps succeed, STL file exists |
| `test_workflow_sketch_pad` | Sketch-based design | New doc -> Sketch -> Body -> Pad -> Export | All steps succeed |
| `test_workflow_multi_export` | Multi-format export | New doc -> Box -> Export STEP+STL+BREP+OBJ | All 4 files exist |
| `test_workflow_save_reopen` | Save and reopen | New doc -> Box -> Save -> Close -> Open -> Verify | Object count preserved |
| `test_workflow_complex_part` | Complex part design | New doc -> Cylinder -> Cut -> Chamfer -> Mirror -> Export | All operations succeed |

---

## Test Suite 14: Error Handling & Edge Cases

**File**: `tests/integration/test_error_handling.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_no_document_operations` | Operations without doc | Call `object_list()` without creating doc | `status == "error"` |
| `test_invalid_object_type` | Invalid type | `object_create("Invalid::Type", "X")` | `status == "error"` |
| `test_empty_object_name` | Empty name | `object_create("Part::Box", "")` | FreeCAD handles (may error or auto-name) |
| `test_negative_dimensions` | Negative values | `object_create("Part::Box", "B", {"Length": -10})` | FreeCAD handles (may error or clamp) |
| `test_zero_dimensions` | Zero values | `object_create("Part::Box", "B", {"Length": 0})` | FreeCAD handles (may error) |
| `test_very_large_values` | Large values | `object_create("Part::Box", "B", {"Length": 1e6})` | `status == "ok"` or error |
| `test_special_characters_in_name` | Special chars | `object_create("Part::Box", "Box-1_test")` | `status == "ok"` |
| `test_timeout_handling` | Operation timeout | Set very short timeout, run complex op | Raises `TimeoutError` |

---

## Test Suite 15: RPC Backend (requires FreeCAD GUI)

**File**: `tests/integration/test_rpc_backend.py`

| Test | Description | Steps | Expected Result |
|------|-------------|-------|-----------------|
| `test_rpc_connect` | Connect to RPC server | `RPCBackend().connect()` | `is_connected() == True` |
| `test_rpc_ping` | Ping server | `_ping()` | Returns `True` |
| `test_rpc_document_new` | Create doc via RPC | `document_new("Test")` | `status == "ok"` |
| `test_rpc_disconnect` | Disconnect | `disconnect()` | `is_connected() == False` |
| `test_rpc_reconnect` | Reconnect | `disconnect(); connect()` | `is_connected() == True` |
| `test_rpc_no_server` | No server running | `RPCBackend(port=19999).connect()` | Raises `ConnectionError` |

---

## Running the Tests

### Quick Verification (smoke test)
```bash
python -m pytest packages/core/tests/integration/ -v -k "test_connect or test_document_new or test_object_create_box" --tb=short
```

### Full Integration Suite
```bash
python -m pytest packages/core/tests/integration/ -v --tb=short
```

### Specific Suite
```bash
python -m pytest packages/core/tests/integration/test_export.py -v --tb=short
```

### With Coverage
```bash
python -m pytest packages/core/tests/integration/ --cov=fc_core --cov-report=term-missing -v
```

---

## Known Limitations to Test Around

1. **HeadlessBackend subprocess overhead**: Each operation spawns a new FreeCADCmd process (~1-3s). Tests should use `session`-scoped fixtures where possible.
2. **No shared state between headless calls**: Each macro runs in a fresh FreeCAD instance. Document state is NOT preserved between `_execute_macro` calls. This is a critical limitation — the current `HeadlessBackend` implementation does NOT maintain a persistent document across calls.
3. **Windows path escaping**: Use raw strings `r"..."` for file paths in macro generation.
4. **RPCBackend requires FreeCAD GUI**: Must have FreeCAD running with MCP addon for RPC tests.

---

## Critical Issue to Investigate

The current `HeadlessBackend` implementation has a **fundamental design issue**: each `_execute_macro` call spawns a **new FreeCADCmd process** with a **fresh FreeCAD instance**. This means:

- `document_new()` creates a document in one process
- `object_create()` runs in a **different** process where that document does not exist
- Multi-step workflows (create doc -> add objects -> export) will **fail** because state is not preserved

**This must be addressed before integration tests can pass.** Options:
1. **Persistent process mode**: Keep FreeCADCmd running as a long-lived process and feed it scripts via stdin
2. **Single-script mode**: Accumulate all operations into one macro script and execute them in a single process
3. **Document serialization**: Save the document after each operation and reopen it in the next call

The integration tests above are designed assuming this issue is resolved (option 2 is most aligned with the current architecture).
