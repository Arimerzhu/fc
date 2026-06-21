"""Tests for sketch MCP tools: sketch_new, sketch_add_line, sketch_add_circle, etc."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_sketch_backend(mock_backend):
    """Patch _get_backend in the sketch tools module."""
    from unittest.mock import patch

    def _factory(backend_type="headless", **kwargs):
        return mock_backend

    with patch("fc_mcp.tools.sketch._get_backend", side_effect=_factory):
        yield mock_backend


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------

class TestSketchToolRegistration:
    """Verify sketch tools are properly registered with MCP."""

    EXPECTED_TOOLS = [
        "sketch_new",
        "sketch_add_line",
        "sketch_add_circle",
        "sketch_add_rect",
        "sketch_add_arc",
        "sketch_add_polygon",
        "sketch_constrain_coincident",
        "sketch_constrain_horizontal",
        "sketch_constrain_vertical",
        "sketch_constrain_distance",
        "sketch_constrain_radius",
        "sketch_get_info",
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
# sketch_new tests
# ---------------------------------------------------------------------------

class TestSketchNew:
    """Test sketch_new tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_new
        result = sketch_new()
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_new
        result = sketch_new(name="MySketch")
        assert result["status"] == "ok"
        assert result["operation"] == "sketch_new"

    def test_default_parameters(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_new
        result = sketch_new()
        assert result["status"] == "ok"
        assert result["data"]["name"] == "Sketch"

    def test_custom_plane(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_new
        result = sketch_new(name="XZSketch", plane="XZ", offset=5.0)
        assert result["status"] == "ok"
        assert result["data"]["plane"] == "XZ"
        assert result["data"]["offset"] == 5.0


# ---------------------------------------------------------------------------
# sketch_add_line tests
# ---------------------------------------------------------------------------

class TestSketchAddLine:
    """Test sketch_add_line tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_add_line
        result = sketch_add_line(sketch_name="Sketch")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_add_line
        result = sketch_add_line(sketch_name="Sketch", start_x=0, start_y=0, end_x=10, end_y=10)
        assert result["status"] == "ok"
        assert result["operation"] == "execute_code"

    def test_requires_sketch_name(self):
        from fc_mcp.tools.sketch import sketch_add_line
        with pytest.raises(TypeError):
            sketch_add_line()

    def test_default_coordinates(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_add_line
        result = sketch_add_line(sketch_name="Sketch")
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# sketch_add_circle tests
# ---------------------------------------------------------------------------

class TestSketchAddCircle:
    """Test sketch_add_circle tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_add_circle
        result = sketch_add_circle(sketch_name="Sketch")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_add_circle
        result = sketch_add_circle(sketch_name="Sketch", center_x=5.0, center_y=5.0, radius=10.0)
        assert result["status"] == "ok"

    def test_requires_sketch_name(self):
        from fc_mcp.tools.sketch import sketch_add_circle
        with pytest.raises(TypeError):
            sketch_add_circle()


# ---------------------------------------------------------------------------
# sketch_add_rect tests
# ---------------------------------------------------------------------------

class TestSketchAddRect:
    """Test sketch_add_rect tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_add_rect
        result = sketch_add_rect(sketch_name="Sketch")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_add_rect
        result = sketch_add_rect(sketch_name="Sketch", corner_x=0, corner_y=0, width=20, height=10)
        assert result["status"] == "ok"

    def test_requires_sketch_name(self):
        from fc_mcp.tools.sketch import sketch_add_rect
        with pytest.raises(TypeError):
            sketch_add_rect()


# ---------------------------------------------------------------------------
# sketch_add_arc tests
# ---------------------------------------------------------------------------

class TestSketchAddArc:
    """Test sketch_add_arc tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_add_arc
        result = sketch_add_arc(sketch_name="Sketch")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_add_arc
        result = sketch_add_arc(sketch_name="Sketch", radius=5.0, start_angle=0.0, end_angle=180.0)
        assert result["status"] == "ok"

    def test_requires_sketch_name(self):
        from fc_mcp.tools.sketch import sketch_add_arc
        with pytest.raises(TypeError):
            sketch_add_arc()


# ---------------------------------------------------------------------------
# sketch_add_polygon tests
# ---------------------------------------------------------------------------

class TestSketchAddPolygon:
    """Test sketch_add_polygon tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_add_polygon
        result = sketch_add_polygon(sketch_name="Sketch")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_add_polygon
        result = sketch_add_polygon(sketch_name="Sketch", sides=6, radius=10.0)
        assert result["status"] == "ok"

    def test_requires_sketch_name(self):
        from fc_mcp.tools.sketch import sketch_add_polygon
        with pytest.raises(TypeError):
            sketch_add_polygon()


# ---------------------------------------------------------------------------
# sketch_constrain_coincident tests
# ---------------------------------------------------------------------------

class TestSketchConstrainCoincident:
    """Test sketch_constrain_coincident tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_constrain_coincident
        result = sketch_constrain_coincident(sketch_name="Sketch", vertex1=0, vertex2=1)
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_constrain_coincident
        result = sketch_constrain_coincident(sketch_name="Sketch", vertex1=0, vertex2=1)
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# sketch_constrain_horizontal tests
# ---------------------------------------------------------------------------

class TestSketchConstrainHorizontal:
    """Test sketch_constrain_horizontal tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_constrain_horizontal
        result = sketch_constrain_horizontal(sketch_name="Sketch", edge_index=0)
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_constrain_horizontal
        result = sketch_constrain_horizontal(sketch_name="Sketch", edge_index=0)
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# sketch_constrain_vertical tests
# ---------------------------------------------------------------------------

class TestSketchConstrainVertical:
    """Test sketch_constrain_vertical tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_constrain_vertical
        result = sketch_constrain_vertical(sketch_name="Sketch", edge_index=0)
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_constrain_vertical
        result = sketch_constrain_vertical(sketch_name="Sketch", edge_index=0)
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# sketch_constrain_distance tests
# ---------------------------------------------------------------------------

class TestSketchConstrainDistance:
    """Test sketch_constrain_distance tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_constrain_distance
        result = sketch_constrain_distance(sketch_name="Sketch", element1=0, element2=1, value=10.0)
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_constrain_distance
        result = sketch_constrain_distance(sketch_name="Sketch", element1=0, element2=1, value=25.4)
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# sketch_constrain_radius tests
# ---------------------------------------------------------------------------

class TestSketchConstrainRadius:
    """Test sketch_constrain_radius tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_constrain_radius
        result = sketch_constrain_radius(sketch_name="Sketch", arc_index=0, radius=5.0)
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_constrain_radius
        result = sketch_constrain_radius(sketch_name="Sketch", arc_index=0, radius=7.5)
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# sketch_get_info tests
# ---------------------------------------------------------------------------

class TestSketchGetInfo:
    """Test sketch_get_info tool."""

    def test_returns_dict(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_get_info
        result = sketch_get_info(sketch_name="Sketch")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_get_info
        result = sketch_get_info(sketch_name="Sketch")
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# Dict format validation
# ---------------------------------------------------------------------------

class TestDictFormat:
    """Verify sketch tool responses follow the expected dict format."""

    def test_ok_response_has_required_keys(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_new
        result = sketch_new(name="FormatTest")
        assert "status" in result
        assert "operation" in result
        assert result["status"] == "ok"

    def test_data_key_present_in_ok(self, mock_sketch_backend):
        from fc_mcp.tools.sketch import sketch_new
        result = sketch_new(name="DataKeyTest")
        assert "data" in result
        assert isinstance(result["data"], dict)


# ---------------------------------------------------------------------------
# Tool signature / schema tests
# ---------------------------------------------------------------------------

class TestToolSignatures:
    """Verify sketch tool functions have correct signatures."""

    def test_sketch_new_has_docstring(self):
        from fc_mcp.tools.sketch import sketch_new
        assert sketch_new.__doc__ is not None
        assert "sketch" in sketch_new.__doc__.lower()

    def test_sketch_add_line_has_docstring(self):
        from fc_mcp.tools.sketch import sketch_add_line
        assert sketch_add_line.__doc__ is not None
        assert "line" in sketch_add_line.__doc__.lower()

    def test_sketch_add_circle_has_docstring(self):
        from fc_mcp.tools.sketch import sketch_add_circle
        assert sketch_add_circle.__doc__ is not None
        assert "circle" in sketch_add_circle.__doc__.lower()

    def test_all_tools_return_dict(self):
        import inspect
        from fc_mcp.tools import sketch as sketch_mod

        tool_functions = [
            getattr(sketch_mod, name)
            for name in dir(sketch_mod)
            if name.startswith("sketch_") and callable(getattr(sketch_mod, name))
        ]
        assert len(tool_functions) >= 3
        for func in tool_functions:
            sig = inspect.signature(func)
            ret = sig.return_annotation
            assert ret is dict or ret == "dict", (
                f"{func.__name__} should return dict, got {ret!r}"
            )
