"""E2E integration tests with real FreeCAD.
Requires FreeCAD 1.1+ installed.
Set FREECAD_PATH env var or ensure FreeCADCmd is on PATH.
"""
from __future__ import annotations

import os
import sys
import json
import time
import tempfile
import subprocess
import pytest

# Ensure FreeCAD can be found
os.environ.setdefault("FREECAD_PATH", r"C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe")

from fc_core.backend import HeadlessBackend, find_freecad
from fc_core.types import ToolResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class Timer:
    """Simple context manager for timing operations."""
    def __init__(self):
        self.elapsed = 0.0
    def __enter__(self):
        self._start = time.perf_counter()
        return self
    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self._start


# Collect timing data for the report
_timing_data: dict[str, float] = {}

@pytest.fixture(scope="module")
def backend():
    """Create a HeadlessBackend with real FreeCAD."""
    be = HeadlessBackend()
    be.connect()
    yield be
    be.disconnect()


@pytest.fixture(autouse=True)
def _fresh_doc(backend):
    """Ensure each test starts with a fresh document."""
    backend.document_new("E2EDoc")
    yield
    # Cleanup: close the document
    try:
        backend.document_close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Test: FreeCAD Discovery
# ---------------------------------------------------------------------------

class TestFreeCADDiscovery:
    """Test FreeCAD can be found on the system."""

    def test_find_freecad_returns_path(self):
        with Timer() as t:
            path = find_freecad()
        _timing_data["find_freecad"] = t.elapsed
        assert path is not None
        assert os.path.isfile(path)

    def test_find_freecad_gui(self):
        with Timer() as t:
            path = find_freecad(gui_required=True)
        _timing_data["find_freecad_gui"] = t.elapsed
        assert path is not None
        assert os.path.isfile(path)

    def test_version(self):
        with Timer() as t:
            be = HeadlessBackend()
            be.connect()
            ver = be.get_version()
            be.disconnect()
        _timing_data["get_version"] = t.elapsed
        assert ver is not None
        assert any(c.isdigit() for c in ver)


# ---------------------------------------------------------------------------
# Test: Document Lifecycle
# ---------------------------------------------------------------------------

class TestDocumentLifecycle:
    """Test document create/save/open/close."""

    def test_document_new(self):
        with Timer() as t:
            be = HeadlessBackend()
            be.connect()
            r = be.document_new("E2ETest")
            be.disconnect()
        _timing_data["document_new"] = t.elapsed
        assert r.status == "ok", f"Failed to create doc: {r}"
        assert r.data.get("name") == "E2ETest"

    def test_document_save(self, tmp_path):
        be = HeadlessBackend()
        be.connect()
        be.document_new("SaveTest")
        out = str(tmp_path / "test_save.FCStd")
        with Timer() as t:
            r = be.document_save(out)
        _timing_data["document_save"] = t.elapsed
        assert r.status == "ok", f"Save failed: {r}"
        assert os.path.isfile(out)
        be.disconnect()

    def test_document_info(self):
        with Timer() as t:
            r = self._backend.document_info()
        _timing_data["document_info"] = t.elapsed
        assert r.status == "ok"
        assert r.data.get("name") == "E2EDoc"

    def test_document_close(self):
        be = HeadlessBackend()
        be.connect()
        be.document_new("CloseTest")
        with Timer() as t:
            r = be.document_close()
        _timing_data["document_close"] = t.elapsed
        assert r.status == "ok"
        be.disconnect()

    @pytest.fixture(autouse=True)
    def _setup_backend(self, backend):
        self._backend = backend


# ---------------------------------------------------------------------------
# Test: Part Primitives (via object_create)
# ---------------------------------------------------------------------------

class TestPartPrimitives:
    """Test creating 3D primitives via real FreeCAD."""

    def test_add_box(self, backend):
        with Timer() as t:
            r = backend.object_create("Part::Box", "Box", {
                "Length": 20, "Width": 15, "Height": 10
            })
        _timing_data["add_box"] = t.elapsed
        assert r.status == "ok", f"Box failed: {r}"
        assert r.data.get("type_id") == "Part::Box"

    def test_add_cylinder(self, backend):
        with Timer() as t:
            r = backend.object_create("Part::Cylinder", "Cylinder", {
                "Radius": 5, "Height": 20
            })
        _timing_data["add_cylinder"] = t.elapsed
        assert r.status == "ok", f"Cylinder failed: {r}"
        assert r.data.get("type_id") == "Part::Cylinder"

    def test_add_sphere(self, backend):
        with Timer() as t:
            r = backend.object_create("Part::Sphere", "Sphere", {
                "Radius": 8
            })
        _timing_data["add_sphere"] = t.elapsed
        assert r.status == "ok", f"Sphere failed: {r}"
        assert r.data.get("type_id") == "Part::Sphere"

    def test_add_cone(self, backend):
        with Timer() as t:
            r = backend.object_create("Part::Cone", "Cone", {
                "Radius1": 10, "Radius2": 3, "Height": 15
            })
        _timing_data["add_cone"] = t.elapsed
        assert r.status == "ok", f"Cone failed: {r}"
        assert r.data.get("type_id") == "Part::Cone"

    def test_add_torus(self, backend):
        with Timer() as t:
            r = backend.object_create("Part::Torus", "Torus", {
                "Radius1": 10, "Radius2": 2
            })
        _timing_data["add_torus"] = t.elapsed
        assert r.status == "ok", f"Torus failed: {r}"
        assert r.data.get("type_id") == "Part::Torus"


# ---------------------------------------------------------------------------
# Test: Object Operations
# ---------------------------------------------------------------------------

class TestObjectOperations:
    """Test object_get, object_list, object_edit, object_delete."""

    def test_object_list(self, backend):
        backend.object_create("Part::Box", "MyBox", {"Length": 10, "Width": 10, "Height": 10})
        with Timer() as t:
            r = backend.object_list()
        _timing_data["object_list"] = t.elapsed
        assert r.status == "ok"
        assert r.data.get("count", 0) >= 1

    def test_object_get(self, backend):
        backend.object_create("Part::Box", "GetBox", {"Length": 10, "Width": 10, "Height": 10})
        with Timer() as t:
            r = backend.object_get("GetBox")
        _timing_data["object_get"] = t.elapsed
        assert r.status == "ok"
        assert r.data.get("name") == "GetBox"
        assert r.data.get("type_id") == "Part::Box"

    def test_object_edit(self, backend):
        backend.object_create("Part::Box", "EditBox", {"Length": 10, "Width": 10, "Height": 10})
        with Timer() as t:
            r = backend.object_edit("EditBox", {"Length": 50})
        _timing_data["object_edit"] = t.elapsed
        assert r.status == "ok"

    def test_object_delete(self, backend):
        backend.object_create("Part::Box", "DelBox", {"Length": 10, "Width": 10, "Height": 10})
        with Timer() as t:
            r = backend.object_delete("DelBox")
        _timing_data["object_delete"] = t.elapsed
        assert r.status == "ok"


# ---------------------------------------------------------------------------
# Test: Export
# ---------------------------------------------------------------------------

class TestExport:
    """Test exporting to various formats."""

    def test_export_step(self, backend, tmp_path):
        backend.object_create("Part::Box", "Box", {"Length": 20, "Width": 15, "Height": 10})
        out = str(tmp_path / "test.step")
        with Timer() as t:
            r = backend.export(out, "step")
        _timing_data["export_step"] = t.elapsed
        assert r.status == "ok", f"STEP export failed: {r}"
        assert os.path.isfile(out)

    def test_export_stl(self, backend, tmp_path):
        backend.object_create("Part::Box", "Box", {"Length": 20, "Width": 15, "Height": 10})
        out = str(tmp_path / "test.stl")
        with Timer() as t:
            r = backend.export(out, "stl")
        _timing_data["export_stl"] = t.elapsed
        assert r.status == "ok", f"STL export failed: {r}"
        assert os.path.isfile(out)

    def test_export_brep(self, backend, tmp_path):
        backend.object_create("Part::Box", "Box", {"Length": 20, "Width": 15, "Height": 10})
        out = str(tmp_path / "test.brep")
        with Timer() as t:
            r = backend.export(out, "brep")
        _timing_data["export_brep"] = t.elapsed
        assert r.status == "ok", f"BREP export failed: {r}"
        assert os.path.isfile(out)

    def test_export_obj(self, backend, tmp_path):
        backend.object_create("Part::Box", "Box", {"Length": 20, "Width": 15, "Height": 10})
        out = str(tmp_path / "test.obj")
        with Timer() as t:
            r = backend.export(out, "obj")
        _timing_data["export_obj"] = t.elapsed
        assert r.status == "ok", f"OBJ export failed: {r}"
        assert os.path.isfile(out)


# ---------------------------------------------------------------------------
# Test: Batch Mode
# ---------------------------------------------------------------------------

class TestBatchMode:
    """Test batch execution for multi-step workflows."""

    def test_batch_document_and_box(self):
        """Create doc + add box in single batch."""
        be = HeadlessBackend()
        be.connect()
        be.batch_start()
        be.batch_add('doc = FreeCAD.newDocument("BatchTest")')
        be.batch_add('box = doc.addObject("Part::Box", "BatchBox")')
        be.batch_add('box.Length = 20')
        be.batch_add('box.Width = 15')
        be.batch_add('box.Height = 10')
        be.batch_add('doc.recompute()')
        with Timer() as t:
            results = be.batch_execute()
        _timing_data["batch_document_and_box"] = t.elapsed
        assert len(results) == 6
        assert results[0]["status"] == "ok"
        assert results[1]["status"] == "ok"
        be.disconnect()

    def test_batch_multiple_primitives(self):
        """Create doc + multiple primitives in single batch."""
        be = HeadlessBackend()
        be.connect()
        be.batch_start()
        be.batch_add('doc = FreeCAD.newDocument("MultiPrim")')
        be.batch_add('b = doc.addObject("Part::Box", "B")')
        be.batch_add('b.Length = 10; b.Width = 10; b.Height = 10')
        be.batch_add('c = doc.addObject("Part::Cylinder", "C")')
        be.batch_add('c.Radius = 5; c.Height = 20')
        be.batch_add('s = doc.addObject("Part::Sphere", "S")')
        be.batch_add('s.Radius = 8')
        be.batch_add('doc.recompute()')
        with Timer() as t:
            results = be.batch_execute()
        _timing_data["batch_multiple_primitives"] = t.elapsed
        assert len(results) == 7
        assert all(r["status"] == "ok" for r in results)
        be.disconnect()

    def test_batch_boolean_union(self):
        """Create two boxes and fuse them in a batch."""
        be = HeadlessBackend()
        be.connect()
        be.batch_start()
        be.batch_add('import FreeCAD')
        be.batch_add('import Part')
        be.batch_add('doc = FreeCAD.newDocument("BoolTest")')
        be.batch_add('b1 = doc.addObject("Part::Box", "B1")')
        be.batch_add('b1.Length = 20; b1.Width = 10; b1.Height = 10')
        be.batch_add('b2 = doc.addObject("Part::Box", "B2")')
        be.batch_add('b2.Placement.Base = FreeCAD.Vector(10, 0, 0)')
        be.batch_add('b2.Length = 10; b2.Width = 10; b2.Height = 10')
        be.batch_add('doc.recompute()')
        be.batch_add('fuse = doc.addObject("Part::MultiFuse", "Fuse")')
        be.batch_add('fuse.Shapes = [b1, b2]')
        be.batch_add('doc.recompute()')
        with Timer() as t:
            results = be.batch_execute()
        _timing_data["batch_boolean_union"] = t.elapsed
        assert len(results) == 10
        assert all(r["status"] == "ok" for r in results)
        be.disconnect()


# ---------------------------------------------------------------------------
# Test: Execute Code
# ---------------------------------------------------------------------------

class TestExecuteCode:
    """Test raw code execution."""

    def test_execute_math(self, backend):
        r = backend.execute_code("import math; print(math.pi)")
        assert r.status == "ok"

    def test_execute_freecad_api(self, backend):
        code = """\
import FreeCAD
doc = FreeCAD.ActiveDocument
print(f"Active doc: {doc.Name}, objects: {len(doc.Objects)}")
"""
        r = backend.execute_code(code)
        assert r.status == "ok"


# ---------------------------------------------------------------------------
# Test: Boolean Operations
# ---------------------------------------------------------------------------

class TestBooleanOperations:
    """Test boolean operations via real FreeCAD."""

    def test_boolean_union(self, backend):
        backend.object_create("Part::Box", "Base", {"Length": 20, "Width": 10, "Height": 10})
        backend.object_create("Part::Box", "Tool", {"Length": 10, "Width": 10, "Height": 10})
        with Timer() as t:
            r = backend.boolean_union("Base", "Tool")
        _timing_data["boolean_union"] = t.elapsed
        assert r.status == "ok", f"Boolean union failed: {r}"

    def test_boolean_cut(self, backend):
        backend.object_create("Part::Box", "Base2", {"Length": 20, "Width": 10, "Height": 10})
        backend.object_create("Part::Box", "Tool2", {"Length": 10, "Width": 10, "Height": 10})
        with Timer() as t:
            r = backend.boolean_cut("Base2", "Tool2")
        _timing_data["boolean_cut"] = t.elapsed
        assert r.status == "ok", f"Boolean cut failed: {r}"


# ---------------------------------------------------------------------------
# Test: Feature Operations
# ---------------------------------------------------------------------------

class TestFeatureOperations:
    """Test fillet, chamfer, mirror, scale."""

    def test_fillet(self, backend):
        backend.object_create("Part::Box", "FilletBox", {"Length": 20, "Width": 10, "Height": 10})
        with Timer() as t:
            r = backend.fillet_edges("FilletBox", radius=1.0)
        _timing_data["fillet"] = t.elapsed
        assert r.status == "ok", f"Fillet failed: {r}"

    def test_chamfer(self, backend):
        backend.object_create("Part::Box", "ChamferBox", {"Length": 20, "Width": 10, "Height": 10})
        with Timer() as t:
            r = backend.chamfer_edges("ChamferBox", size=1.0)
        _timing_data["chamfer"] = t.elapsed
        assert r.status == "ok", f"Chamfer failed: {r}"

    def test_mirror(self, backend):
        backend.object_create("Part::Box", "MirrorBox", {"Length": 20, "Width": 10, "Height": 10})
        with Timer() as t:
            r = backend.mirror_object("MirrorBox", plane="XY")
        _timing_data["mirror"] = t.elapsed
        assert r.status == "ok", f"Mirror failed: {r}"

    def test_scale(self, backend):
        backend.object_create("Part::Box", "ScaleBox", {"Length": 20, "Width": 10, "Height": 10})
        with Timer() as t:
            r = backend.scale_object("ScaleBox", factor=2.0)
        _timing_data["scale"] = t.elapsed
        assert r.status == "ok", f"Scale failed: {r}"


# ---------------------------------------------------------------------------
# Test: Sketch and PartDesign
# ---------------------------------------------------------------------------

class TestSketchAndPartDesign:
    """Test sketch and PartDesign body operations."""

    def test_sketch_new(self, backend):
        with Timer() as t:
            r = backend.sketch_new(plane="XY", name="MySketch")
        _timing_data["sketch_new"] = t.elapsed
        assert r.status == "ok", f"Sketch creation failed: {r}"

    def test_body_new(self, backend):
        with Timer() as t:
            r = backend.body_new("MyBody")
        _timing_data["body_new"] = t.elapsed
        assert r.status == "ok", f"Body creation failed: {r}"


# ---------------------------------------------------------------------------
# Report generation (runs at session end)
# ---------------------------------------------------------------------------

def pytest_sessionfinish(session, exitstatus):
    """Write timing data to a report file after all tests complete."""
    if not _timing_data:
        return
    report_lines = ["# E2E Test Timing Report\n"]
    report_lines.append("| Operation | Time (s) |")
    report_lines.append("|-----------|----------|")
    total = 0.0
    for op, t in sorted(_timing_data.items(), key=lambda x: x[1], reverse=True):
        report_lines.append(f"| {op} | {t:.3f} |")
        total += t
    report_lines.append(f"| **TOTAL** | **{total:.3f}** |")
    report_text = "\n".join(report_lines) + "\n"
    report_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "E2E_TEST_REPORT.md")
    # Append timing section to report
    existing = ""
    if os.path.isfile(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            existing = f.read()
    # Replace or append timing section
    if "# E2E Test Timing Report" in existing:
        idx = existing.index("# E2E Test Timing Report")
        existing = existing[:idx] + report_text
    else:
        existing += "\n" + report_text
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(existing)
