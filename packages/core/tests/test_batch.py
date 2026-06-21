"""Tests for HeadlessBackend batch execution mode.

Covers:
- batch_start() initialization
- batch_add() queuing without execution
- batch_execute() combining operations into a single process call
- batch_execute() result parsing (per-operation markers)
- batch_execute() empty batch returns empty list
- batch_execute() timeout handling
- Multi-step workflow: document_new -> object_create -> document_save in one batch
- Backward compatibility: single-operation interfaces still work
"""

import json
import subprocess
from unittest.mock import MagicMock, patch, call

import pytest

from fc_core.backend import HeadlessBackend
from fc_core.types import ToolResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def backend():
    with patch.object(HeadlessBackend, "freecad_path", new_callable=lambda: property(lambda self: "/fake/freecadcmd")):
        b = HeadlessBackend(freecad_path="/fake/freecadcmd")
        yield b


def _make_stdout(*results: dict) -> str:
    """Build fake stdout with per-operation FC_RESULT markers."""
    lines = []
    for i, r in enumerate(results):
        lines.append(f"___FC_RESULT_{i}___{json.dumps(r)}")
    return "\n".join(lines)


def _mock_run(results: list[dict], returncode: int = 0):
    """Return a mock for _run that produces per-operation markers."""
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.stdout = _make_stdout(*results)
    proc.stderr = ""
    proc.returncode = returncode
    return proc


# ---------------------------------------------------------------------------
# batch_start tests
# ---------------------------------------------------------------------------

class TestBatchStart:
    def test_initializes_empty_batch(self, backend):
        backend.batch_start()
        assert hasattr(backend, "_batch_parts")
        assert backend._batch_parts == []

    def test_resets_existing_batch(self, backend):
        backend.batch_start()
        backend.batch_add("print('hello')")
        backend.batch_start()
        assert backend._batch_parts == []


# ---------------------------------------------------------------------------
# batch_add tests
# ---------------------------------------------------------------------------

class TestBatchAdd:
    def test_accumulates_operations(self, backend):
        backend.batch_start()
        backend.batch_add("op1")
        backend.batch_add("op2")
        assert len(backend._batch_parts) == 2

    def test_does_not_execute_immediately(self, backend):
        backend.batch_start()
        with patch.object(backend, "_run") as mock_run:
            backend.batch_add("doc = FreeCAD.newDocument('test')")
            mock_run.assert_not_called()

    def test_auto_starts_batch_if_not_started(self, backend):
        backend.batch_add("some code")
        assert hasattr(backend, "_batch_parts")
        assert backend._batch_parts == ["some code"]

    def test_preserves_order(self, backend):
        backend.batch_start()
        backend.batch_add("first")
        backend.batch_add("second")
        backend.batch_add("third")
        assert backend._batch_parts == ["first", "second", "third"]


# ---------------------------------------------------------------------------
# batch_execute tests
# ---------------------------------------------------------------------------

class TestBatchExecute:
    def test_merges_operations_to_single_process_call(self, backend):
        backend.batch_start()
        backend.batch_add("doc = FreeCAD.newDocument('Batched')")
        backend.batch_add("obj = doc.addObject('Part::Box', 'Box')")

        mock_result = _mock_run([
            {"status": "ok", "data": {"name": "Batched", "label": "Batched"}, "message": ""},
            {"status": "ok", "data": {"name": "Box", "label": "Box"}, "message": ""},
        ])
        with patch.object(backend, "_run", return_value=mock_result) as mock_run, \
             patch.object(backend, "_write_macro", return_value="/tmp/test.py"):
            results = backend.batch_execute()

        assert mock_run.call_count == 1
        assert len(results) == 2

    def test_returns_result_list_per_operation(self, backend):
        backend.batch_start()
        backend.batch_add("doc = FreeCAD.newDocument('Doc1')")
        backend.batch_add("doc2 = FreeCAD.newDocument('Doc2')")

        mock_result = _mock_run([
            {"status": "ok", "data": {"name": "Doc1"}, "message": "created"},
            {"status": "ok", "data": {"name": "Doc2"}, "message": "created"},
        ])
        with patch.object(backend, "_run", return_value=mock_result), \
             patch.object(backend, "_write_macro", return_value="/tmp/test.py"):
            results = backend.batch_execute()

        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["data"]["name"] == "Doc1"
        assert results[1]["data"]["name"] == "Doc2"

    def test_empty_batch_returns_empty_list(self, backend):
        backend.batch_start()
        results = backend.batch_execute()
        assert results == []

    def test_batch_without_start_returns_empty_list(self, backend):
        results = backend.batch_execute()
        assert results == []

    def test_single_operation(self, backend):
        backend.batch_start()
        backend.batch_add("doc = FreeCAD.newDocument('Single')")

        mock_result = _mock_run([
            {"status": "ok", "data": {"name": "Single"}, "message": ""},
        ])
        with patch.object(backend, "_run", return_value=mock_result), \
             patch.object(backend, "_write_macro", return_value="/tmp/test.py"):
            results = backend.batch_execute()

        assert len(results) == 1
        assert results[0]["status"] == "ok"

    def test_clears_batch_after_execution(self, backend):
        backend.batch_start()
        backend.batch_add("x = 1")

        mock_result = _mock_run([
            {"status": "ok", "data": {}, "message": ""},
        ])
        with patch.object(backend, "_run", return_value=mock_result), \
             patch.object(backend, "_write_macro", return_value="/tmp/test.py"):
            backend.batch_execute()

        assert backend._batch_parts == []

    def test_timeout_raises_timeout_error(self, backend):
        backend.batch_start()
        backend.batch_add("import time; time.sleep(999)")

        with patch.object(backend, "_run", side_effect=TimeoutError("FreeCAD process timed out after 1s")), \
             patch.object(backend, "_write_macro", return_value="/tmp/test.py"):
            with pytest.raises(TimeoutError):
                backend.batch_execute(timeout=1)

    def test_custom_timeout_overrides_default(self, backend):
        backend.batch_start()
        backend.batch_add("print('test')")

        mock_result = _mock_run([
            {"status": "ok", "data": {}, "message": ""},
        ])
        with patch.object(backend, "_run", return_value=mock_result) as mock_run, \
             patch.object(backend, "_write_macro", return_value="/tmp/test.py"):
            backend.batch_execute(timeout=30)

        # Verify the timeout was forwarded to _run
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert kwargs.get("timeout") == 30

    def test_pad_missing_results_with_error(self, backend):
        """If stdout has fewer markers than batch parts, pad with error results."""
        backend.batch_start()
        backend.batch_add("op1")
        backend.batch_add("op2")
        backend.batch_add("op3")

        # Only one result marker in stdout
        proc = MagicMock(spec=subprocess.CompletedProcess)
        proc.stdout = "___FC_RESULT_0___" + json.dumps({"status": "ok", "data": {}, "message": ""}) + "\n"
        proc.stderr = ""
        proc.returncode = 0

        with patch.object(backend, "_run", return_value=proc), \
             patch.object(backend, "_write_macro", return_value="/tmp/test.py"):
            results = backend.batch_execute()

        assert len(results) == 3
        assert results[0]["status"] == "ok"
        assert results[1]["status"] == "error"
        assert results[2]["status"] == "error"

    def test_mixed_success_and_error_results(self, backend):
        backend.batch_start()
        backend.batch_add("good_op")
        backend.batch_add("bad_op")

        mock_result = _mock_run([
            {"status": "ok", "data": {"result": 42}, "message": ""},
            {"status": "error", "data": {}, "message": "Something went wrong"},
        ])
        with patch.object(backend, "_run", return_value=mock_result), \
             patch.object(backend, "_write_macro", return_value="/tmp/test.py"):
            results = backend.batch_execute()

        assert results[0]["status"] == "ok"
        assert results[0]["data"]["result"] == 42
        assert results[1]["status"] == "error"
        assert "Something went wrong" in results[1]["message"]


# ---------------------------------------------------------------------------
# Multi-step workflow test
# ---------------------------------------------------------------------------

class TestBatchWorkflow:
    def test_document_new_object_create_document_save(self, backend):
        """Full workflow: create doc, add object, save -- in a single batch_execute."""
        backend.batch_start()
        backend.batch_add("doc = FreeCAD.newDocument('WorkflowDoc')")
        backend.batch_add("box = doc.addObject('Part::Box', 'MyBox')")
        backend.batch_add("doc.recompute()")
        backend.batch_add("doc.saveAs('/tmp/workflow.fcstd')")

        mock_result = _mock_run([
            {"status": "ok", "data": {"name": "WorkflowDoc", "label": "WorkflowDoc"}, "message": ""},
            {"status": "ok", "data": {"name": "MyBox", "label": "MyBox"}, "message": ""},
            {"status": "ok", "data": {}, "message": "recomputed"},
            {"status": "ok", "data": {"saved_to": "/tmp/workflow.fcstd"}, "message": ""},
        ])
        with patch.object(backend, "_run", return_value=mock_result) as mock_run, \
             patch.object(backend, "_write_macro", return_value="/tmp/workflow.py") as mock_write:
            results = backend.batch_execute()

        # All 4 operations executed in one process call
        assert mock_run.call_count == 1
        assert len(results) == 4
        assert all(r["status"] == "ok" for r in results)

        # Macro file was written and cleaned up
        mock_write.assert_called_once()

    def test_workflow_all_ok_statuses(self, backend):
        backend.batch_start()
        backend.batch_add("step1")
        backend.batch_add("step2")

        mock_result = _mock_run([
            {"status": "ok", "data": {}, "message": "step1 done"},
            {"status": "ok", "data": {}, "message": "step2 done"},
        ])
        with patch.object(backend, "_run", return_value=mock_result), \
             patch.object(backend, "_write_macro", return_value="/tmp/test.py"):
            results = backend.batch_execute()

        assert results[0]["message"] == "step1 done"
        assert results[1]["message"] == "step2 done"


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    def test_document_new_still_works(self, backend):
        """Single document_new call returns ToolResponse (not batch list)."""
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {"name": "Doc", "label": "Doc"}, "message": ""
        }):
            r = backend.document_new("TestDoc")
        assert isinstance(r, ToolResponse)
        assert r.status == "ok"
        assert r.operation == "document_new"

    def test_document_save_still_works(self, backend):
        backend._current_doc_path = "/tmp/existing.fcstd"
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {"saved_to": "/tmp/existing.fcstd"}, "message": ""
        }):
            r = backend.document_save()
        assert isinstance(r, ToolResponse)
        assert r.status == "ok"
        assert r.operation == "document_save"

    def test_object_create_still_works(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {"name": "Box", "label": "Box", "type_id": "Part::Box"}, "message": ""
        }):
            r = backend.object_create("Part::Box", "Box")
        assert isinstance(r, ToolResponse)
        assert r.status == "ok"
        assert r.operation == "object_create"

    def test_execute_code_still_works(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {"result": 42}, "message": "done"
        }):
            r = backend.execute_code("print(42)")
        assert isinstance(r, ToolResponse)
        assert r.status == "ok"
        assert r.operation == "execute_code"

    def test_batch_does_not_affect_single_operations(self, backend):
        """Running a batch does not change behavior of subsequent single ops."""
        # Run a batch first
        backend.batch_start()
        backend.batch_add("x = 1")
        mock_result = _mock_run([
            {"status": "ok", "data": {}, "message": ""},
        ])
        with patch.object(backend, "_run", return_value=mock_result), \
             patch.object(backend, "_write_macro", return_value="/tmp/test.py"):
            batch_results = backend.batch_execute()

        assert isinstance(batch_results, list)

        # Now run a single operation -- should still return ToolResponse
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {"name": "AfterBatch", "label": "AfterBatch"}, "message": ""
        }):
            single_result = backend.document_new("AfterBatch")

        assert isinstance(single_result, ToolResponse)
        assert single_result.status == "ok"

    def test_single_ops_without_batch_return_tool_response(self, backend):
        """Calling single methods without batch_start returns ToolResponse objects."""
        for method_name, kwargs, expected_op in [
            ("document_new", {"name": "X"}, "document_new"),
            ("object_list", {}, "object_list"),
        ]:
            method = getattr(backend, method_name)
            with patch.object(backend, "_execute_macro", return_value={
                "status": "ok", "data": {}, "message": ""
            }):
                r = method(**kwargs)
            assert isinstance(r, ToolResponse), f"{method_name} must return ToolResponse"
            assert r.operation == expected_op
