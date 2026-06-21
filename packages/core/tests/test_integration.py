"""Integration tests that require real FreeCAD.

These tests verify end-to-end functionality with a real FreeCAD installation.
They are SKIPPED automatically when FreeCAD is not available.

Run all integration tests:
    pytest packages/core/tests/test_integration.py -v

Run only integration tests (skip others):
    pytest -m integration

Run with coverage:
    pytest packages/core/tests/test_integration.py -v --cov=fc_core.backend --cov-report=term-missing
"""

from __future__ import annotations

import os
import shutil

import pytest

# Skip all tests in this module if FreeCAD is not installed
freecad_path = shutil.which("FreeCADCmd") or shutil.which("freecadcmd")
pytestmark = [
    pytest.mark.skipif(
        freecad_path is None,
        reason="FreeCAD not installed — skipping integration tests",
    ),
    pytest.mark.integration,
]


@pytest.fixture(scope="module")
def backend():
    """Create a connected HeadlessBackend for the test module."""
    from fc_core.backend import HeadlessBackend

    be = HeadlessBackend()
    be.connect()
    yield be
    be.disconnect()


@pytest.fixture(autouse=True)
def _fresh_document(backend):
    """Each test gets a fresh document and cleanup after."""
    backend.document_new("IntegrationTest")
    yield
    try:
        backend.document_close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 1. test_document_new_and_save
# ---------------------------------------------------------------------------

class TestDocumentNewAndSave:
    """Create a document, save it, verify the file exists."""

    def test_document_new_and_save(self, backend, tmp_path):
        out = str(tmp_path / "saved_doc.FCStd")
        # Save the auto-created document
        result = backend.document_save(out)
        assert result.status == "ok", f"Save failed: {result}"
        assert os.path.isfile(out), f"Saved file not found: {out}"
        assert os.path.getsize(out) > 0, "Saved file is empty"


# ---------------------------------------------------------------------------
# 2. test_part_add_box
# ---------------------------------------------------------------------------

class TestPartAddBox:
    """Create a Box and verify the object exists in the document."""

    def test_part_add_box(self, backend):
        result = backend.object_create("Part::Box", "TestBox", {
            "Length": 20, "Width": 15, "Height": 10,
        })
        assert result.status == "ok", f"Box creation failed: {result}"
        assert result.data.get("type_id") == "Part::Box"

        # Verify the object is listed
        objects = backend.object_list()
        assert objects.status == "ok"
        names = [o["name"] for o in objects.data.get("objects", [])]
        assert "TestBox" in names


# ---------------------------------------------------------------------------
# 3. test_part_add_cylinder
# ---------------------------------------------------------------------------

class TestPartAddCylinder:
    """Create a Cylinder and verify the object exists."""

    def test_part_add_cylinder(self, backend):
        result = backend.object_create("Part::Cylinder", "TestCylinder", {
            "Radius": 10, "Height": 30,
        })
        assert result.status == "ok", f"Cylinder creation failed: {result}"
        assert result.data.get("type_id") == "Part::Cylinder"


# ---------------------------------------------------------------------------
# 4. test_boolean_union
# ---------------------------------------------------------------------------

class TestBooleanUnion:
    """Create two boxes and fuse them with boolean union."""

    def test_boolean_union(self, backend):
        # Create two overlapping boxes
        r1 = backend.object_create("Part::Box", "UnionBase", {
            "Length": 20, "Width": 10, "Height": 10,
        })
        assert r1.status == "ok"

        r2 = backend.object_create("Part::Box", "UnionTool", {
            "Length": 10, "Width": 10, "Height": 10,
        })
        assert r2.status == "ok"

        # Fuse them
        result = backend.boolean_union("UnionBase", "UnionTool")
        assert result.status == "ok", f"Boolean union failed: {result}"
        assert result.data.get("name") is not None


# ---------------------------------------------------------------------------
# 5. test_export_step
# ---------------------------------------------------------------------------

class TestExportSTEP:
    """Export to STEP and verify file size > 0."""

    def test_export_step(self, backend, tmp_path):
        backend.object_create("Part::Box", "ExportBox", {
            "Length": 20, "Width": 15, "Height": 10,
        })
        out = str(tmp_path / "export_test.step")
        result = backend.export(out, "step")
        assert result.status == "ok", f"STEP export failed: {result}"
        assert os.path.isfile(out), f"STEP file not created: {out}"
        assert os.path.getsize(out) > 0, "STEP file is empty"


# ---------------------------------------------------------------------------
# 6. test_export_stl
# ---------------------------------------------------------------------------

class TestExportSTL:
    """Export to STL and verify file exists."""

    def test_export_stl(self, backend, tmp_path):
        backend.object_create("Part::Box", "STLBox", {
            "Length": 20, "Width": 15, "Height": 10,
        })
        out = str(tmp_path / "export_test.stl")
        result = backend.export(out, "stl")
        assert result.status == "ok", f"STL export failed: {result}"
        assert os.path.isfile(out), f"STL file not created: {out}"
        assert os.path.getsize(out) > 0, "STL file is empty"


# ---------------------------------------------------------------------------
# 7. test_multi_step_workflow
# ---------------------------------------------------------------------------

class TestMultiStepWorkflow:
    """Complete workflow: document -> create parts -> boolean -> export."""

    def test_multi_step_workflow(self, backend, tmp_path):
        # Document is already created by fixture

        # Step 1: Create base box
        r1 = backend.object_create("Part::Box", "WfBox", {
            "Length": 30, "Width": 20, "Height": 10,
        })
        assert r1.status == "ok", f"Box failed: {r1}"

        # Step 2: Create cylinder to cut
        r2 = backend.object_create("Part::Cylinder", "WfCyl", {
            "Radius": 5, "Height": 10,
        })
        assert r2.status == "ok", f"Cylinder failed: {r2}"

        # Step 3: Boolean cut
        r3 = backend.boolean_cut("WfBox", "WfCyl")
        assert r3.status == "ok", f"Boolean cut failed: {r3}"

        # Step 4: Export STEP
        step_path = str(tmp_path / "workflow.step")
        r4 = backend.export(step_path, "step")
        assert r4.status == "ok", f"Export failed: {r4}"
        assert os.path.isfile(step_path)

        # Step 5: Export STL
        stl_path = str(tmp_path / "workflow.stl")
        r5 = backend.export(stl_path, "stl")
        assert r5.status == "ok", f"STL export failed: {r5}"
        assert os.path.isfile(stl_path)


# ---------------------------------------------------------------------------
# 8. test_batch_operations
# ---------------------------------------------------------------------------

class TestBatchOperations:
    """Test batch_start / batch_add / batch_execute three-step workflow."""

    def test_batch_operations(self):
        """Create doc, add box, recompute, and export — all in one batch."""
        from fc_core.backend import HeadlessBackend

        be = HeadlessBackend()
        be.connect()

        try:
            be.batch_start()
            be.batch_add('doc = FreeCAD.newDocument("BatchInteg")')
            be.batch_add('box = doc.addObject("Part::Box", "BatchBox")')
            be.batch_add('box.Length = 25')
            be.batch_add('box.Width = 15')
            be.batch_add('box.Height = 10')
            be.batch_add('doc.recompute()')

            results = be.batch_execute()

            assert len(results) == 6, f"Expected 6 results, got {len(results)}"
            assert all(
                r.get("status") == "ok" for r in results
            ), f"Some operations failed: {results}"
        finally:
            be.disconnect()
