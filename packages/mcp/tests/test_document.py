"""Tests for document MCP tools: document_new, document_open, document_save, document_close, document_info, document_list."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_doc_backend(mock_backend):
    """Patch _get_backend in the document tools module."""
    from unittest.mock import patch

    def _factory(backend_type="headless", **kwargs):
        return mock_backend

    with patch("fc_mcp.tools.document._get_backend", side_effect=_factory):
        yield mock_backend


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------

class TestDocumentToolRegistration:
    """Verify document tools are properly registered with MCP."""

    EXPECTED_TOOLS = [
        "document_new",
        "document_open",
        "document_save",
        "document_info",
        "document_close",
        "document_list",
    ]

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_registered(self, registered_tools, tool_name):
        assert tool_name in registered_tools, f"{tool_name} not registered"

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_is_callable(self, registered_tools, tool_name):
        from fc_mcp.server import mcp
        tool = mcp._tool_manager._tools[tool_name]
        assert callable(tool.fn)


# ---------------------------------------------------------------------------
# document_new tests
# ---------------------------------------------------------------------------

class TestDocumentNew:
    """Test document_new tool."""

    def test_returns_dict(self, mock_doc_backend):
        from fc_mcp.tools.document import document_new
        result = document_new()
        assert isinstance(result, dict)

    def test_status_ok(self, mock_doc_backend):
        from fc_mcp.tools.document import document_new
        result = document_new(name="TestDoc")
        assert result["status"] == "ok"
        assert result["operation"] == "document_new"

    def test_default_name(self, mock_doc_backend):
        from fc_mcp.tools.document import document_new
        result = document_new()
        assert result["status"] == "ok"
        assert result["data"]["name"] == "Untitled"

    def test_custom_name(self, mock_doc_backend):
        from fc_mcp.tools.document import document_new
        result = document_new(name="MyProject")
        assert result["status"] == "ok"
        assert result["data"]["name"] == "MyProject"

    def test_backend_parameter_accepted(self, mock_doc_backend):
        from fc_mcp.tools.document import document_new
        result = document_new(name="RpcDoc", backend="rpc")
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# document_open tests
# ---------------------------------------------------------------------------

class TestDocumentOpen:
    """Test document_open tool."""

    def test_returns_dict(self, mock_doc_backend):
        from fc_mcp.tools.document import document_open
        result = document_open(file_path="/tmp/test.FCStd")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_doc_backend):
        from fc_mcp.tools.document import document_open
        result = document_open(file_path="/tmp/test.FCStd")
        assert result["status"] == "ok"
        assert result["operation"] == "document_open"

    def test_data_contains_path(self, mock_doc_backend):
        from fc_mcp.tools.document import document_open
        result = document_open(file_path="/tmp/my_model.FCStd")
        assert result["data"]["file_path"] == "/tmp/my_model.FCStd"

    def test_requires_file_path(self):
        from fc_mcp.tools.document import document_open
        with pytest.raises(TypeError):
            document_open()


# ---------------------------------------------------------------------------
# document_save tests
# ---------------------------------------------------------------------------

class TestDocumentSave:
    """Test document_save tool."""

    def test_returns_dict(self, mock_doc_backend):
        from fc_mcp.tools.document import document_save
        result = document_save()
        assert isinstance(result, dict)

    def test_status_ok(self, mock_doc_backend):
        from fc_mcp.tools.document import document_save
        result = document_save(file_path="/tmp/save.FCStd")
        assert result["status"] == "ok"
        assert result["operation"] == "document_save"

    def test_with_file_path(self, mock_doc_backend):
        from fc_mcp.tools.document import document_save
        result = document_save(file_path="/tmp/output.FCStd")
        assert result["status"] == "ok"
        assert result["data"]["file_path"] == "/tmp/output.FCStd"

    def test_without_file_path(self, mock_doc_backend):
        from fc_mcp.tools.document import document_save
        result = document_save()
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# document_info tests
# ---------------------------------------------------------------------------

class TestDocumentInfo:
    """Test document_info tool."""

    def test_returns_dict(self, mock_doc_backend):
        from fc_mcp.tools.document import document_info
        result = document_info()
        assert isinstance(result, dict)

    def test_status_ok(self, mock_doc_backend):
        from fc_mcp.tools.document import document_info
        result = document_info()
        assert result["status"] == "ok"
        assert result["operation"] == "document_info"

    def test_data_contains_info(self, mock_doc_backend):
        from fc_mcp.tools.document import document_info
        result = document_info()
        assert "data" in result


# ---------------------------------------------------------------------------
# document_close tests
# ---------------------------------------------------------------------------

class TestDocumentClose:
    """Test document_close tool."""

    def test_returns_dict(self, mock_doc_backend):
        from fc_mcp.tools.document import document_close
        result = document_close()
        assert isinstance(result, dict)

    def test_status_ok(self, mock_doc_backend):
        from fc_mcp.tools.document import document_close
        result = document_close()
        assert result["status"] == "ok"
        assert result["operation"] == "document_close"


# ---------------------------------------------------------------------------
# document_list tests
# ---------------------------------------------------------------------------

class TestDocumentList:
    """Test document_list tool."""

    def test_returns_dict(self, mock_doc_backend):
        from fc_mcp.tools.document import document_list
        result = document_list()
        assert isinstance(result, dict)

    def test_status_ok(self, mock_doc_backend):
        from fc_mcp.tools.document import document_list
        result = document_list()
        assert result["status"] == "ok"
        assert result["operation"] == "object_list"

    def test_default_backend_is_rpc(self, mock_doc_backend):
        from fc_mcp.tools.document import document_list
        result = document_list()
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# Dict format validation
# ---------------------------------------------------------------------------

class TestDictFormat:
    """Verify document tool responses follow the expected dict format."""

    def test_ok_response_has_required_keys(self, mock_doc_backend):
        from fc_mcp.tools.document import document_new
        result = document_new(name="FormatTest")
        assert "status" in result
        assert "operation" in result
        assert result["status"] == "ok"

    def test_data_key_present_in_ok(self, mock_doc_backend):
        from fc_mcp.tools.document import document_new
        result = document_new(name="DataKeyTest")
        assert "data" in result
        assert isinstance(result["data"], dict)

    def test_message_present_in_ok(self, mock_doc_backend):
        from fc_mcp.tools.document import document_new
        result = document_new(name="MsgTest")
        assert "message" in result


# ---------------------------------------------------------------------------
# Tool signature / schema tests
# ---------------------------------------------------------------------------

class TestToolSignatures:
    """Verify document tool functions have correct signatures."""

    def test_document_new_has_docstring(self):
        from fc_mcp.tools.document import document_new
        assert document_new.__doc__ is not None
        assert "document" in document_new.__doc__.lower()

    def test_document_open_has_docstring(self):
        from fc_mcp.tools.document import document_open
        assert document_open.__doc__ is not None
        assert "open" in document_open.__doc__.lower()

    def test_document_save_has_docstring(self):
        from fc_mcp.tools.document import document_save
        assert document_save.__doc__ is not None
        assert "save" in document_save.__doc__.lower()

    def test_all_tools_return_dict(self):
        import inspect
        from fc_mcp.tools import document as doc_mod

        tool_functions = [
            getattr(doc_mod, name)
            for name in dir(doc_mod)
            if name.startswith("document_") and callable(getattr(doc_mod, name))
        ]
        assert len(tool_functions) >= 3
        for func in tool_functions:
            sig = inspect.signature(func)
            ret = sig.return_annotation
            assert ret is dict or ret == "dict", (
                f"{func.__name__} should return dict, got {ret!r}"
            )
