"""Tests for execute MCP tools: execute_code, execute_file."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_exec_backend(mock_backend):
    """Patch _get_backend in the execute tools module."""
    from unittest.mock import patch

    def _factory(backend_type="headless", **kwargs):
        return mock_backend

    with patch("fc_mcp.tools.execute._get_backend", side_effect=_factory):
        yield mock_backend


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------

class TestExecuteToolRegistration:
    """Verify execute tools are properly registered with MCP."""

    EXPECTED_TOOLS = [
        "execute_code",
        "execute_file",
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
# execute_code tests
# ---------------------------------------------------------------------------

class TestExecuteCode:
    """Test execute_code tool."""

    def test_returns_dict(self, mock_exec_backend):
        from fc_mcp.tools.execute import execute_code
        result = execute_code(code="print('hello')")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_exec_backend):
        from fc_mcp.tools.execute import execute_code
        result = execute_code(code="1 + 1")
        assert result["status"] == "ok"
        assert result["operation"] == "execute_code"

    def test_data_contains_code(self, mock_exec_backend):
        from fc_mcp.tools.execute import execute_code
        result = execute_code(code="x = 42")
        assert result["data"]["code"] == "x = 42"

    def test_requires_code(self):
        from fc_mcp.tools.execute import execute_code
        with pytest.raises(TypeError):
            execute_code()

    def test_timeout_parameter(self, mock_exec_backend):
        from fc_mcp.tools.execute import execute_code
        result = execute_code(code="pass", timeout=60)
        assert result["status"] == "ok"

    def test_backend_parameter_accepted(self, mock_exec_backend):
        from fc_mcp.tools.execute import execute_code
        result = execute_code(code="pass", backend="rpc")
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# execute_file tests
# ---------------------------------------------------------------------------

class TestExecuteFile:
    """Test execute_file tool."""

    def test_returns_dict(self, mock_exec_backend, tmp_path):
        from fc_mcp.tools.execute import execute_file
        macro = tmp_path / "test_macro.py"
        macro.write_text("print('hello')")
        result = execute_file(file_path=str(macro))
        assert isinstance(result, dict)

    def test_status_ok(self, mock_exec_backend, tmp_path):
        from fc_mcp.tools.execute import execute_file
        macro = tmp_path / "test_macro.py"
        macro.write_text("x = 1")
        result = execute_file(file_path=str(macro))
        assert result["status"] == "ok"
        assert result["operation"] == "execute_code"

    def test_requires_file_path(self):
        from fc_mcp.tools.execute import execute_file
        with pytest.raises(TypeError):
            execute_file()

    def test_file_not_found(self, mock_exec_backend):
        from fc_mcp.tools.execute import execute_file
        result = execute_file(file_path="/nonexistent/path/macro.py")
        assert result["status"] == "error"
        assert result["error"]["code"] == "FILE_NOT_FOUND"

    def test_timeout_parameter(self, mock_exec_backend, tmp_path):
        from fc_mcp.tools.execute import execute_file
        macro = tmp_path / "test_macro.py"
        macro.write_text("pass")
        result = execute_file(file_path=str(macro), timeout=30)
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# Dict format validation
# ---------------------------------------------------------------------------

class TestDictFormat:
    """Verify execute tool responses follow the expected dict format."""

    def test_ok_response_has_required_keys(self, mock_exec_backend):
        from fc_mcp.tools.execute import execute_code
        result = execute_code(code="test")
        assert "status" in result
        assert "operation" in result
        assert result["status"] == "ok"

    def test_data_key_present_in_ok(self, mock_exec_backend):
        from fc_mcp.tools.execute import execute_code
        result = execute_code(code="test")
        assert "data" in result
        assert isinstance(result["data"], dict)

    def test_error_response_has_error_key(self, mock_exec_backend):
        from fc_mcp.tools.execute import execute_file
        result = execute_file(file_path="/nonexistent/macro.py")
        assert result["status"] == "error"
        assert "error" in result
        assert "code" in result["error"]
        assert "message" in result["error"]


# ---------------------------------------------------------------------------
# Tool signature / schema tests
# ---------------------------------------------------------------------------

class TestToolSignatures:
    """Verify execute tool functions have correct signatures."""

    def test_execute_code_has_docstring(self):
        from fc_mcp.tools.execute import execute_code
        assert execute_code.__doc__ is not None
        assert "code" in execute_code.__doc__.lower()

    def test_execute_file_has_docstring(self):
        from fc_mcp.tools.execute import execute_file
        assert execute_file.__doc__ is not None
        assert "file" in execute_file.__doc__.lower()

    def test_all_tools_return_dict(self):
        import inspect
        from fc_mcp.tools import execute as exec_mod

        tool_functions = [
            getattr(exec_mod, name)
            for name in dir(exec_mod)
            if name.startswith("execute_") and callable(getattr(exec_mod, name))
        ]
        assert len(tool_functions) >= 2
        for func in tool_functions:
            sig = inspect.signature(func)
            ret = sig.return_annotation
            assert ret is dict or ret == "dict", (
                f"{func.__name__} should return dict, got {ret!r}"
            )
