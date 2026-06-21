"""Extended tests for fc_core backend module.

Covers:
- All public methods return ToolResponse (success and error paths)
- Convenience export methods (export_step, export_stl, etc.)
- Convenience import methods (import_step, import_stl, etc.)
- Query aliases (list_objects, get_object_info, get_objects_info)
- transform_placement method
- Batch operations on RPCBackend (no-op)
- RPCBackend interface compliance
"""

from unittest.mock import MagicMock, patch

import pytest

from fc_core.backend import (
    BackendInterface,
    HeadlessBackend,
    RPCBackend,
)
from fc_core.types import ToolResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def headless_backend():
    with patch.object(HeadlessBackend, "freecad_path", new_callable=lambda: property(lambda self: "/fake/freecadcmd")):
        b = HeadlessBackend(freecad_path="/fake/freecadcmd")
        yield b


def _ok_macro(data=None):
    return {"status": "ok", "data": data or {}, "message": ""}


def _err_macro(msg="error"):
    return {"status": "error", "data": {}, "message": msg}


# ---------------------------------------------------------------------------
# HeadlessBackend: convenience export methods
# ---------------------------------------------------------------------------


class TestHeadlessBackendExportConvenience:
    """Test that convenience export methods delegate to export()."""

    @pytest.mark.parametrize("method_name,expected_fmt", [
        ("export_step", "step"),
        ("export_stl", "stl"),
        ("export_obj", "obj"),
        ("export_brep", "brep"),
        ("export_dxf", "dxf"),
        ("export_svg", "svg"),
        ("export_gltf", "gltf"),
        ("export_3mf", "3mf"),
        ("export_fcstd", "fcstd"),
    ])
    def test_convenience_export_methods(self, headless_backend, method_name, expected_fmt):
        with patch.object(headless_backend, "export", return_value=ToolResponse.ok("export")) as mock_export:
            method = getattr(headless_backend, method_name)
            r = method("/tmp/test.file")
            mock_export.assert_called_once_with("/tmp/test.file", expected_fmt)

    def test_export_pdf_delegates_to_svg(self, headless_backend):
        with patch.object(headless_backend, "export", return_value=ToolResponse.ok("export")) as mock_export:
            r = headless_backend.export_pdf("/tmp/test.pdf")
            mock_export.assert_called_once_with("/tmp/test.pdf", "svg")


# ---------------------------------------------------------------------------
# HeadlessBackend: convenience import methods
# ---------------------------------------------------------------------------


class TestHeadlessBackendImportConvenience:
    """Test that convenience import methods delegate to _import_file()."""

    @pytest.mark.parametrize("method_name", [
        "import_step", "import_stl", "import_obj", "import_dxf", "import_brep",
    ])
    def test_convenience_import_methods(self, headless_backend, method_name):
        with patch.object(headless_backend, "_import_file", return_value=ToolResponse.ok("import")) as mock_import:
            method = getattr(headless_backend, method_name)
            r = method("/tmp/test.file")
            mock_import.assert_called_once()


# ---------------------------------------------------------------------------
# HeadlessBackend: query aliases
# ---------------------------------------------------------------------------


class TestHeadlessBackendQueryAliases:
    """Test that query aliases delegate to their canonical methods."""

    def test_list_objects_delegates_to_object_list(self, headless_backend):
        with patch.object(headless_backend, "_execute_macro", return_value=_ok_macro({"objects": [], "count": 0})):
            r = headless_backend.list_objects()
        assert isinstance(r, ToolResponse)
        assert r.status == "ok"

    def test_get_object_info_delegates_to_object_get(self, headless_backend):
        with patch.object(headless_backend, "_execute_macro", return_value=_ok_macro({"name": "Box", "type_id": "Part::Box"})):
            r = headless_backend.get_object_info("Box")
        assert isinstance(r, ToolResponse)
        assert r.status == "ok"

    def test_get_objects_info_delegates_to_object_list(self, headless_backend):
        with patch.object(headless_backend, "_execute_macro", return_value=_ok_macro({"objects": [], "count": 0})):
            r = headless_backend.get_objects_info()
        assert isinstance(r, ToolResponse)
        assert r.status == "ok"


# ---------------------------------------------------------------------------
# HeadlessBackend: transform_placement
# ---------------------------------------------------------------------------


class TestHeadlessBackendTransformPlacement:
    """Test transform_placement method."""

    def test_transform_position(self, headless_backend):
        with patch.object(headless_backend, "_execute_macro", return_value=_ok_macro()):
            r = headless_backend.transform_placement("Obj", position=(10, 20, 30))
        assert isinstance(r, ToolResponse)
        assert r.status == "ok"
        assert r.operation == "transform_placement"

    def test_transform_rotation(self, headless_backend):
        with patch.object(headless_backend, "_execute_macro", return_value=_ok_macro()):
            r = headless_backend.transform_placement("Obj", rotation=(45, 90, 0))
        assert r.status == "ok"

    def test_transform_both(self, headless_backend):
        with patch.object(headless_backend, "_execute_macro", return_value=_ok_macro()):
            r = headless_backend.transform_placement("Obj", position=(1, 2, 3), rotation=(4, 5, 6))
        assert r.status == "ok"

    def test_transform_error(self, headless_backend):
        with patch.object(headless_backend, "_execute_macro", return_value=_err_macro("not found")):
            r = headless_backend.transform_placement("Missing")
        assert r.status == "error"
        assert r.error_code == "TRANSFORM_FAILED"


# ---------------------------------------------------------------------------
# HeadlessBackend: all methods return ToolResponse (success)
# ---------------------------------------------------------------------------


class TestHeadlessBackendAllMethodsReturnToolResponse:
    """Verify every public method returns ToolResponse on success."""

    @pytest.mark.parametrize("method_name,kwargs", [
        ("document_new", {"name": "TestDoc"}),
        ("document_open", {"file_path": "/tmp/test.fcstd"}),
        ("document_save", {"file_path": "/tmp/test.fcstd"}),
        ("document_info", {}),
        ("document_close", {}),
        ("object_list", {}),
        ("object_get", {"obj_name": "Box"}),
        ("object_create", {"obj_type": "Part::Box", "obj_name": "Box"}),
        ("object_edit", {"obj_name": "Box", "properties": {"Length": 20}}),
        ("object_delete", {"obj_name": "Box"}),
        ("sketch_new", {}),
        ("body_new", {}),
        ("body_pad", {"body_name": "Body", "sketch_name": "Sketch"}),
        ("boolean_union", {"base_name": "A", "tool_name": "B"}),
        ("boolean_cut", {"base_name": "A", "tool_name": "B"}),
        ("boolean_common", {"obj1_name": "A", "obj2_name": "B"}),
        ("fillet_edges", {"obj_name": "Box"}),
        ("chamfer_edges", {"obj_name": "Box"}),
        ("mirror_object", {"obj_name": "Box"}),
        ("scale_object", {"obj_name": "Box", "factor": 2.0}),
        ("export", {"file_path": "/tmp/test.step", "verify": False}),
        ("execute_code", {"code": "print('hello')"}),
        ("transform_placement", {"obj_name": "Box"}),
        ("list_objects", {}),
        ("get_object_info", {"obj_name": "Box"}),
        ("get_objects_info", {}),
    ])
    def test_method_returns_tool_response_ok(self, headless_backend, method_name, kwargs):
        with patch.object(headless_backend, "_execute_macro", return_value=_ok_macro()):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.getsize", return_value=1024):
                    with patch("os.makedirs"):
                        method = getattr(headless_backend, method_name)
                        r = method(**kwargs)
        assert isinstance(r, ToolResponse), f"{method_name} must return ToolResponse"
        assert r.status == "ok", f"{method_name} should return ok"


# ---------------------------------------------------------------------------
# HeadlessBackend: all methods return ToolResponse on error
# ---------------------------------------------------------------------------


class TestHeadlessBackendAllMethodsReturnToolResponseError:
    """Verify every public method returns ToolResponse on error."""

    @pytest.mark.parametrize("method_name,kwargs,expected_error_code", [
        ("document_new", {"name": "TestDoc"}, "CREATE_FAILED"),
        ("document_open", {"file_path": "/tmp/test.fcstd"}, "OPEN_FAILED"),
        ("document_save", {"file_path": "/tmp/test.fcstd"}, "SAVE_FAILED"),
        ("document_info", {}, "INFO_FAILED"),
        ("document_close", {}, "CLOSE_FAILED"),
        ("object_list", {}, "LIST_FAILED"),
        ("object_get", {"obj_name": "Box"}, "GET_FAILED"),
        ("object_create", {"obj_type": "Part::Box", "obj_name": "Box"}, "CREATE_FAILED"),
        ("object_edit", {"obj_name": "Box", "properties": {}}, "EDIT_FAILED"),
        ("object_delete", {"obj_name": "Box"}, "DELETE_FAILED"),
        ("sketch_new", {}, "CREATE_FAILED"),
        ("body_new", {}, "CREATE_FAILED"),
        ("body_pad", {"body_name": "Body", "sketch_name": "Sketch"}, "PAD_FAILED"),
        ("boolean_union", {"base_name": "A", "tool_name": "B"}, "BOOLEAN_FAILED"),
        ("boolean_cut", {"base_name": "A", "tool_name": "B"}, "BOOLEAN_FAILED"),
        ("boolean_common", {"obj1_name": "A", "obj2_name": "B"}, "BOOLEAN_FAILED"),
        ("fillet_edges", {"obj_name": "Box"}, "FILLET_FAILED"),
        ("chamfer_edges", {"obj_name": "Box"}, "CHAMFER_FAILED"),
        ("mirror_object", {"obj_name": "Box"}, "MIRROR_FAILED"),
        ("scale_object", {"obj_name": "Box", "factor": 2.0}, "SCALE_FAILED"),
        ("execute_code", {"code": "bad"}, "EXEC_FAILED"),
    ])
    def test_method_returns_tool_response_error(self, headless_backend, method_name, kwargs, expected_error_code):
        with patch.object(headless_backend, "_execute_macro", return_value=_err_macro("test error")):
            method = getattr(headless_backend, method_name)
            r = method(**kwargs)
        assert isinstance(r, ToolResponse), f"{method_name} must return ToolResponse on error"
        assert r.status == "error", f"{method_name} should return error status"
        assert r.error_code == expected_error_code, f"{method_name} wrong error_code: {r.error_code}"


# ---------------------------------------------------------------------------
# RPCBackend: interface compliance
# ---------------------------------------------------------------------------


class TestRPCBackendInterfaceCompliance:
    """Verify RPCBackend implements all BackendInterface abstract methods."""

    def test_is_subclass(self):
        assert issubclass(RPCBackend, BackendInterface)

    def test_all_abstract_methods_implemented(self):
        abstract_methods = {
            name for name, val in BackendInterface.__dict__.items()
            if getattr(val, "__isabstractmethod__", False)
        }
        for method_name in abstract_methods:
            assert hasattr(RPCBackend, method_name), \
                f"RPCBackend missing abstract method: {method_name}"


# ---------------------------------------------------------------------------
# RPCBackend: batch operations are no-ops
# ---------------------------------------------------------------------------


class TestRPCBackendBatchNoOp:
    """RPCBackend batch methods should be safe no-ops."""

    def test_batch_start_no_error(self):
        backend = RPCBackend()
        backend.batch_start()  # Should not raise

    def test_batch_add_no_error(self):
        backend = RPCBackend()
        backend.batch_add("print('hello')")  # Should not raise

    def test_batch_execute_returns_empty(self):
        backend = RPCBackend()
        result = backend.batch_execute()
        assert result == []


# ---------------------------------------------------------------------------
# RPCBackend: convenience methods
# ---------------------------------------------------------------------------


class TestRPCBackendConvenienceMethods:
    """Test RPCBackend convenience export/import methods."""

    @pytest.fixture
    def rpc_backend(self):
        backend = RPCBackend()
        backend._server = MagicMock()
        backend._connected = True
        return backend

    @pytest.mark.parametrize("method_name,expected_fmt", [
        ("export_step", "step"),
        ("export_stl", "stl"),
        ("export_obj", "obj"),
        ("export_brep", "brep"),
        ("export_dxf", "dxf"),
        ("export_svg", "svg"),
        ("export_gltf", "gltf"),
        ("export_3mf", "3mf"),
        ("export_fcstd", "fcstd"),
    ])
    def test_convenience_export_methods(self, rpc_backend, method_name, expected_fmt):
        with patch.object(rpc_backend, "export", return_value=ToolResponse.ok("export")) as mock_export:
            method = getattr(rpc_backend, method_name)
            r = method("/tmp/test.file")
            mock_export.assert_called_once_with("/tmp/test.file", expected_fmt)

    @pytest.mark.parametrize("method_name", [
        "import_step", "import_stl", "import_obj", "import_dxf", "import_brep",
    ])
    def test_convenience_import_methods(self, rpc_backend, method_name):
        with patch.object(rpc_backend, "_import_file", return_value=ToolResponse.ok("import")) as mock_import:
            method = getattr(rpc_backend, method_name)
            r = method("/tmp/test.file")
            mock_import.assert_called_once()


# ---------------------------------------------------------------------------
# RPCBackend: query aliases
# ---------------------------------------------------------------------------


class TestRPCBackendQueryAliases:
    """Test RPCBackend query aliases."""

    @pytest.fixture
    def rpc_backend(self):
        backend = RPCBackend()
        backend._server = MagicMock()
        backend._connected = True
        return backend

    def test_list_objects(self, rpc_backend):
        rpc_backend._server.get_objects.return_value = {"success": True, "objects": []}
        r = rpc_backend.list_objects()
        assert isinstance(r, ToolResponse)

    def test_get_object_info(self, rpc_backend):
        rpc_backend._server.get_object.return_value = {"success": True, "name": "Box"}
        r = rpc_backend.get_object_info("Box")
        assert isinstance(r, ToolResponse)

    def test_get_objects_info(self, rpc_backend):
        rpc_backend._server.get_objects.return_value = {"success": True, "objects": []}
        r = rpc_backend.get_objects_info()
        assert isinstance(r, ToolResponse)


# ---------------------------------------------------------------------------
# RPCBackend: transform_placement
# ---------------------------------------------------------------------------


class TestRPCBackendTransformPlacement:
    """Test RPCBackend transform_placement."""

    @pytest.fixture
    def rpc_backend(self):
        backend = RPCBackend()
        backend._server = MagicMock()
        backend._connected = True
        return backend

    def test_transform_position(self, rpc_backend):
        rpc_backend._server.execute_code.return_value = {"success": True}
        r = rpc_backend.transform_placement("Obj", position=(1, 2, 3))
        assert isinstance(r, ToolResponse)
        assert r.status == "ok"

    def test_transform_error(self, rpc_backend):
        rpc_backend._server.execute_code.return_value = {"success": False, "error": "fail"}
        r = rpc_backend.transform_placement("Missing")
        assert r.status == "error"
        assert r.error_code == "TRANSFORM_FAILED"
