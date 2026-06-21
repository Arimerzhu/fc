"""Tests for query MCP tools: list_objects, get_object, get_object_properties, etc."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_query_backend(mock_backend):
    """Patch _get_backend in the query tools module."""
    from unittest.mock import patch

    def _factory(backend_type="headless", **kwargs):
        return mock_backend

    with patch("fc_mcp.tools.query._get_backend", side_effect=_factory):
        yield mock_backend


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------

class TestQueryToolRegistration:
    """Verify query tools are properly registered with MCP."""

    EXPECTED_TOOLS = [
        "list_objects",
        "get_object",
        "get_object_properties",
        "get_bounding_box",
        "get_shape_info",
        "get_version",
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
# list_objects tests
# ---------------------------------------------------------------------------

class TestListObjects:
    """Test list_objects tool."""

    def test_returns_dict(self, mock_query_backend):
        from fc_mcp.tools.query import list_objects
        result = list_objects()
        assert isinstance(result, dict)

    def test_status_ok(self, mock_query_backend):
        from fc_mcp.tools.query import list_objects
        result = list_objects()
        assert result["status"] == "ok"
        assert result["operation"] == "object_list"

    def test_data_contains_objects(self, mock_query_backend):
        from fc_mcp.tools.query import list_objects
        result = list_objects()
        assert "data" in result


# ---------------------------------------------------------------------------
# get_object tests
# ---------------------------------------------------------------------------

class TestGetObject:
    """Test get_object tool."""

    def test_returns_dict(self, mock_query_backend):
        from fc_mcp.tools.query import get_object
        result = get_object(obj_name="Box")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_query_backend):
        from fc_mcp.tools.query import get_object
        result = get_object(obj_name="Box")
        assert result["status"] == "ok"
        assert result["operation"] == "object_get"

    def test_data_contains_name(self, mock_query_backend):
        from fc_mcp.tools.query import get_object
        result = get_object(obj_name="MyBox")
        assert result["data"]["name"] == "MyBox"

    def test_requires_obj_name(self):
        from fc_mcp.tools.query import get_object
        with pytest.raises(TypeError):
            get_object()


# ---------------------------------------------------------------------------
# get_object_properties tests
# ---------------------------------------------------------------------------

class TestGetObjectProperties:
    """Test get_object_properties tool."""

    def test_returns_dict(self, mock_query_backend):
        from fc_mcp.tools.query import get_object_properties
        result = get_object_properties(obj_name="Box")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_query_backend):
        from fc_mcp.tools.query import get_object_properties
        result = get_object_properties(obj_name="Box")
        assert result["status"] == "ok"
        assert result["operation"] == "execute_code"

    def test_requires_obj_name(self):
        from fc_mcp.tools.query import get_object_properties
        with pytest.raises(TypeError):
            get_object_properties()


# ---------------------------------------------------------------------------
# get_bounding_box tests
# ---------------------------------------------------------------------------

class TestGetBoundingBox:
    """Test get_bounding_box tool."""

    def test_returns_dict(self, mock_query_backend):
        from fc_mcp.tools.query import get_bounding_box
        result = get_bounding_box(obj_name="Box")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_query_backend):
        from fc_mcp.tools.query import get_bounding_box
        result = get_bounding_box(obj_name="Box")
        assert result["status"] == "ok"
        assert result["operation"] == "execute_code"

    def test_requires_obj_name(self):
        from fc_mcp.tools.query import get_bounding_box
        with pytest.raises(TypeError):
            get_bounding_box()


# ---------------------------------------------------------------------------
# get_shape_info tests
# ---------------------------------------------------------------------------

class TestGetShapeInfo:
    """Test get_shape_info tool."""

    def test_returns_dict(self, mock_query_backend):
        from fc_mcp.tools.query import get_shape_info
        result = get_shape_info(obj_name="Box")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_query_backend):
        from fc_mcp.tools.query import get_shape_info
        result = get_shape_info(obj_name="Box")
        assert result["status"] == "ok"
        assert result["operation"] == "execute_code"

    def test_requires_obj_name(self):
        from fc_mcp.tools.query import get_shape_info
        with pytest.raises(TypeError):
            get_shape_info()


# ---------------------------------------------------------------------------
# get_version tests
# ---------------------------------------------------------------------------

class TestGetVersion:
    """Test get_version tool."""

    def test_returns_dict(self, mock_query_backend):
        from fc_mcp.tools.query import get_version
        result = get_version()
        assert isinstance(result, dict)

    def test_status_ok(self, mock_query_backend):
        from fc_mcp.tools.query import get_version
        result = get_version()
        assert result["status"] == "ok"
        assert result["operation"] == "get_version"

    def test_data_contains_version(self, mock_query_backend):
        from fc_mcp.tools.query import get_version
        result = get_version()
        assert "version" in result["data"]

    def test_backend_parameter_accepted(self, mock_query_backend):
        from fc_mcp.tools.query import get_version
        result = get_version(backend="rpc")
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# Dict format validation
# ---------------------------------------------------------------------------

class TestDictFormat:
    """Verify query tool responses follow the expected dict format."""

    def test_ok_response_has_required_keys(self, mock_query_backend):
        from fc_mcp.tools.query import list_objects
        result = list_objects()
        assert "status" in result
        assert "operation" in result
        assert result["status"] == "ok"

    def test_data_key_present_in_ok(self, mock_query_backend):
        from fc_mcp.tools.query import list_objects
        result = list_objects()
        assert "data" in result
        assert isinstance(result["data"], dict)

    def test_get_version_data_has_version(self, mock_query_backend):
        from fc_mcp.tools.query import get_version
        result = get_version()
        assert "version" in result["data"]


# ---------------------------------------------------------------------------
# Tool signature / schema tests
# ---------------------------------------------------------------------------

class TestToolSignatures:
    """Verify query tool functions have correct signatures."""

    def test_list_objects_has_docstring(self):
        from fc_mcp.tools.query import list_objects
        assert list_objects.__doc__ is not None
        assert "object" in list_objects.__doc__.lower()

    def test_get_object_has_docstring(self):
        from fc_mcp.tools.query import get_object
        assert get_object.__doc__ is not None
        assert "object" in get_object.__doc__.lower()

    def test_get_version_has_docstring(self):
        from fc_mcp.tools.query import get_version
        assert get_version.__doc__ is not None
        assert "version" in get_version.__doc__.lower()

    def test_all_tools_return_dict(self):
        import inspect
        from fc_mcp.tools import query as query_mod

        tool_functions = [
            getattr(query_mod, name)
            for name in dir(query_mod)
            if callable(getattr(query_mod, name))
            and not name.startswith("_")
            and name not in ("ToolResponse",)
        ]
        assert len(tool_functions) >= 3
        for func in tool_functions:
            sig = inspect.signature(func)
            ret = sig.return_annotation
            assert ret is dict or ret == "dict", (
                f"{func.__name__} should return dict, got {ret!r}"
            )
