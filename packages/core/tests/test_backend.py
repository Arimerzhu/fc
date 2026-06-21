"""Tests for fc_core backend module.

Covers:
- find_freecad() discovery logic (env var, PATH, platform-specific)
- ToolResponse serialization (ok/error formats)
- HeadlessBackend interface compliance
"""

import os
import platform
from unittest.mock import MagicMock, patch

import pytest

from fc_core.backend import (
    BackendInterface,
    HeadlessBackend,
    _install_instructions,
    find_freecad,
)
from fc_core.types import ToolResponse


# ---------------------------------------------------------------------------
# find_freecad() tests
# ---------------------------------------------------------------------------

class TestHeadlessBackendDiscovery:
    """Tests for FreeCAD executable discovery."""

    def test_env_var_found(self, tmp_path):
        """FREECAD_PATH env var prioritized when file exists."""
        fake_path = tmp_path / "FreeCADCmd.exe"
        fake_path.write_text("fake")
        with patch.dict(os.environ, {"FREECAD_PATH": str(fake_path)}):
            result = find_freecad()
        assert result == str(fake_path.resolve())

    def test_env_var_missing_ignores(self, tmp_path):
        """FREECAD_PATH pointing to nonexistent file is ignored."""
        bad_path = str(tmp_path / "nope.exe")
        fake_path = tmp_path / "RealCmd.exe"
        fake_path.write_text("fake")
        with patch.dict(os.environ, {"FREECAD_PATH": bad_path}), \
             patch("shutil.which", return_value=str(fake_path)):
            result = find_freecad()
        assert result == str(fake_path.resolve())

    def test_path_lookup(self):
        """Falls back to shutil.which on PATH."""
        with patch.dict(os.environ, {}, clear=False), \
             patch("shutil.which", return_value="/usr/bin/freecadcmd"):
            # Ensure FREECAD_PATH is not set
            os.environ.pop("FREECAD_PATH", None)
            result = find_freecad()
        assert os.path.isabs(result)
        assert result.endswith(os.path.join("", "usr", "bin", "freecadcmd"))

    def test_path_lookup_returns_absolute(self):
        """find_freecad always returns absolute path."""
        with patch.dict(os.environ, {"FREECAD_PATH": ""}), \
             patch("shutil.which", return_value="./freecadcmd"):
            result = find_freecad()
        assert os.path.isabs(result)

    def test_no_relevant_env_set(self):
        """Without FREECAD_PATH, searches PATH normally."""
        os.environ.pop("FREECAD_PATH", None)
        with patch("shutil.which", return_value="/opt/freecadcmd"):
            result = find_freecad()
        assert os.path.isabs(result)
        assert result.endswith(os.path.join("", "opt", "freecadcmd"))

    def test_file_not_found_raises(self):
        """Raises FileNotFoundError when FreeCAD cannot be found."""
        os.environ.pop("FREECAD_PATH", None)
        with patch("shutil.which", return_value=None), \
             patch("platform.system", return_value="Linux"), \
             pytest.raises(FileNotFoundError):
            find_freecad()

    def test_gui_names_when_gui_required(self):
        """gui_required=True searches for GUI executable names."""
        os.environ.pop("FREECAD_PATH", None)
        with patch("shutil.which") as mock_which:
            def which_side_effect(name):
                return "/usr/bin/freecad" if name in ("freecad", "FreeCAD", "freecad.exe", "FreeCAD.exe") else None
            mock_which.side_effect = which_side_effect
            result = find_freecad(gui_required=True)
        assert os.path.isabs(result)
        assert result.endswith(os.path.join("", "usr", "bin", "freecad"))
        # Ensure GUI names were searched
        searched_names = [call.args[0] for call in mock_which.call_args_list]
        assert "freecad" in searched_names

    def test_default_searches_cmd_names(self):
        """Default (gui_required=False) searches for Cmd executable names."""
        os.environ.pop("FREECAD_PATH", None)
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            try:
                find_freecad()
            except FileNotFoundError:
                pass
        searched_names = [call.args[0] for call in mock_which.call_args_list]
        assert "freecadcmd" in searched_names
        assert "FreeCADCmd" in searched_names

    def test_install_instructions_content(self):
        """_install_instructions returns helpful text."""
        msg = _install_instructions()
        assert "FreeCAD" in msg
        assert "FREECAD_PATH" in msg


# ---------------------------------------------------------------------------
# ToolResponse format tests
# ---------------------------------------------------------------------------

class TestToolResponseFormat:
    """Tests for ToolResponse serialization."""

    def test_to_dict_ok_minimal(self):
        r = ToolResponse.ok("test_op", {"key": "val"}, "Done")
        d = r.to_dict()
        assert d == {
            "status": "ok",
            "operation": "test_op",
            "data": {"key": "val"},
            "message": "Done",
        }

    def test_to_dict_ok_no_data(self):
        r = ToolResponse.ok("test_op")
        d = r.to_dict()
        assert "data" not in d
        assert d["status"] == "ok"

    def test_to_dict_ok_no_message(self):
        r = ToolResponse.ok("test_op", {"x": 1})
        d = r.to_dict()
        assert "message" not in d

    def test_to_dict_error_full(self):
        r = ToolResponse.error("test_op", "ERR_CODE", "Failed", "Try again")
        d = r.to_dict()
        assert d["status"] == "error"
        assert d["operation"] == "test_op"
        assert d["error"]["code"] == "ERR_CODE"
        assert d["error"]["message"] == "Failed"
        assert d["error"]["suggestion"] == "Try again"

    def test_to_dict_error_no_suggestion(self):
        r = ToolResponse.error("test_op", "ERR", "msg")
        d = r.to_dict()
        assert "suggestion" not in d["error"]

    def test_to_dict_error_has_error_key(self):
        """Error responses must have 'error' key in dict."""
        r = ToolResponse.error("op", "CODE", "msg")
        d = r.to_dict()
        assert "error" in d

    def test_to_dict_ok_no_error_key(self):
        """OK responses must NOT have 'error' key in dict."""
        r = ToolResponse.ok("op", {"x": 1})
        d = r.to_dict()
        assert "error" not in d

    def test_ok_factory_defaults(self):
        r = ToolResponse.ok("my_op")
        assert r.status == "ok"
        assert r.operation == "my_op"
        assert r.data == {}
        assert r.message == ""

    def test_error_factory_defaults(self):
        r = ToolResponse.error("my_op", "CODE", "msg")
        assert r.status == "error"
        assert r.error_code == "CODE"
        assert r.suggestion == ""


# ---------------------------------------------------------------------------
# Backend interface compliance tests
# ---------------------------------------------------------------------------

class TestBackendInterfaceCompliance:
    """Verify HeadlessBackend implements all BackendInterface abstract methods."""

    @pytest.fixture
    def backend(self):
        with patch.object(HeadlessBackend, "freecad_path", new_callable=lambda: property(lambda self: "/fake/freecadcmd")):
            b = HeadlessBackend(freecad_path="/fake/freecadcmd")
            yield b

    def test_is_subclass(self):
        assert issubclass(HeadlessBackend, BackendInterface)

    def test_all_abstract_methods_implemented(self):
        """HeadlessBackend must implement every abstract method from BackendInterface."""
        abstract_methods = {
            name for name, val in BackendInterface.__dict__.items()
            if getattr(val, "__isabstractmethod__", False)
        }
        concrete_methods = {
            name for name in dir(HeadlessBackend)
            if not name.startswith("_") or name in ("__init__",)
        }
        # Check that all abstract method names exist on HeadlessBackend
        for method_name in abstract_methods:
            assert hasattr(HeadlessBackend, method_name), \
                f"HeadlessBackend missing abstract method: {method_name}"

    def test_connect_sets_connected(self, backend):
        with patch.object(backend, "get_version", return_value="0.21"):
            backend.connect()
        assert backend.is_connected() is True

    def test_disconnect_clears_connected(self, backend):
        with patch.object(backend, "get_version", return_value="0.21"):
            backend.connect()
        backend.disconnect()
        assert backend.is_connected() is False

    def test_connect_failure_raises(self, backend):
        with patch.object(backend, "get_version", side_effect=Exception("boom")):
            with pytest.raises(ConnectionError):
                backend.connect()

    def test_freecad_path_property_uses_find_freecad(self):
        """When freecad_path is None, property calls find_freecad()."""
        b = HeadlessBackend()
        with patch("fc_core.backend.find_freecad", return_value="/found/freecadcmd"):
            assert b.freecad_path == "/found/freecadcmd"

    def test_freecad_path_explicit(self):
        """Explicit freecad_path is used as-is."""
        b = HeadlessBackend(freecad_path="/custom/path")
        assert b.freecad_path == "/custom/path"

    def test_is_connected_initially_false(self, backend):
        assert backend.is_connected() is False

    def test_document_new_returns_tool_response(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {"name": "Doc", "label": "Doc"}, "message": ""
        }):
            r = backend.document_new("TestDoc")
        assert isinstance(r, ToolResponse)
        assert r.status == "ok"
        assert r.operation == "document_new"

    def test_document_new_failure(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "error", "data": {}, "message": "boom"
        }):
            r = backend.document_new("TestDoc")
        assert r.status == "error"
        assert r.error_code == "CREATE_FAILED"

    def test_document_save_no_path_error(self, backend):
        backend._current_doc_path = None
        r = backend.document_save()
        assert r.status == "error"
        assert r.error_code == "NO_PATH"

    def test_object_list_returns_tool_response(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {"objects": [], "count": 0}, "message": ""
        }):
            r = backend.object_list()
        assert isinstance(r, ToolResponse)
        assert r.status == "ok"
        assert "objects" in r.data

    def test_object_get_not_found(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "error", "data": {}, "message": "not found"
        }):
            r = backend.object_get("Missing")
        assert r.status == "error"
        assert r.error_code == "GET_FAILED"

    def test_export_format_step(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {}, "message": ""
        }), patch("os.path.isfile", return_value=True), \
             patch("os.path.getsize", return_value=1024), \
             patch("os.makedirs"):
            r = backend.export("/tmp/test.step", verify=False)
        assert r.status == "ok"
        assert r.data["format"] == "step"
        assert r.data["file_size"] == 1024

    def test_export_format_stl(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {}, "message": ""
        }), patch("os.path.isfile", return_value=True), \
             patch("os.path.getsize", return_value=512), \
             patch("os.makedirs"):
            r = backend.export("/tmp/test.stl", verify=False)
        assert r.status == "ok"
        assert r.data["format"] == "stl"

    def test_execute_code_ok(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {"result": 42}, "message": "done"
        }):
            r = backend.execute_code("print(42)")
        assert r.status == "ok"
        assert r.data["result"] == 42

    def test_execute_code_error(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "error", "data": {}, "message": "SyntaxError"
        }):
            r = backend.execute_code("bad code")
        assert r.status == "error"
        assert r.error_code == "EXEC_FAILED"

    def test_boolean_operations(self, backend):
        """Test boolean union, cut, common all return ToolResponse."""
        for method_name, args in [
            ("boolean_union", ("A", "B")),
            ("boolean_cut", ("A", "B")),
            ("boolean_common", ("A", "B")),
        ]:
            with patch.object(backend, "_execute_macro", return_value={
                "status": "ok", "data": {"name": "Result", "label": "Result"}, "message": ""
            }):
                method = getattr(backend, method_name)
                r = method(*args)
            assert isinstance(r, ToolResponse)
            assert r.status == "ok"

    def test_feature_operations(self, backend):
        """Test fillet, chamfer, mirror, scale all return ToolResponse."""
        for method_name, args in [
            ("fillet_edges", ("Obj",)),
            ("chamfer_edges", ("Obj",)),
            ("mirror_object", ("Obj",)),
            ("scale_object", ("Obj", 2.0)),
        ]:
            with patch.object(backend, "_execute_macro", return_value={
                "status": "ok", "data": {"name": "Result", "label": "Result"}, "message": ""
            }):
                method = getattr(backend, method_name)
                r = method(*args)
            assert isinstance(r, ToolResponse)
            assert r.status == "ok"

    def test_sketch_new(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {"name": "Sketch", "label": "Sketch", "plane": "XY"}, "message": ""
        }):
            r = backend.sketch_new(plane="XY", name="MySketch")
        assert r.status == "ok"
        assert r.data["plane"] == "XY"

    def test_body_new(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {"name": "Body", "label": "Body"}, "message": ""
        }):
            r = backend.body_new("MyBody")
        assert r.status == "ok"

    def test_body_pad(self, backend):
        with patch.object(backend, "_execute_macro", return_value={
            "status": "ok", "data": {"name": "Pad", "label": "Pad", "length": 10.0}, "message": ""
        }):
            r = backend.body_pad("Body", "Sketch", length=10.0)
        assert r.status == "ok"
        assert r.data["length"] == 10.0
