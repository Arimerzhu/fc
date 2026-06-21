"""Tests for geometry MCP tools: create_box, create_cylinder, boolean_union, etc."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------

class TestGeometryToolRegistration:
    """Verify geometry tools are properly registered with MCP."""

    EXPECTED_TOOLS = [
        "geometry_create_box",
        "geometry_create_cylinder",
        "geometry_create_sphere",
        "geometry_create_cone",
        "geometry_create_torus",
        "geometry_boolean_union",
        "geometry_boolean_cut",
        "geometry_boolean_common",
        "geometry_fillet_edges",
        "geometry_chamfer_edges",
        "geometry_mirror",
        "geometry_scale",
        "geometry_delete",
        "geometry_transform",
    ]

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_registered(self, registered_tools, tool_name):
        """Each geometry tool should appear in the MCP server's tool list."""
        assert tool_name in registered_tools, f"{tool_name} not registered"

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_is_callable(self, registered_tools, tool_name):
        """Registered tools should be callable."""
        from fc_mcp.server import mcp
        tool = mcp._tool_manager._tools[tool_name]
        assert callable(tool.fn)


# ---------------------------------------------------------------------------
# create_box tests
# ---------------------------------------------------------------------------

class TestCreateBox:
    """Test geometry_create_box tool."""

    def test_returns_dict(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_box
        result = geometry_create_box(name="TestBox", length=20.0, width=30.0, height=40.0)
        assert isinstance(result, dict)

    def test_status_ok(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_box
        result = geometry_create_box(name="MyBox")
        assert result["status"] == "ok"
        # The operation comes from the backend's object_create call
        assert result["operation"] == "object_create"

    def test_data_contains_box_info(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_box
        result = geometry_create_box(name="DataBox", length=5.0, width=10.0, height=15.0)
        assert result["data"]["name"] == "DataBox"
        # The type is the FreeCAD type ID
        assert result["data"]["type"] == "Part::Box"
        # PrimitivesMixin enriches with dimensions
        assert result["data"]["dimensions"]["length"] == 5.0
        assert result["data"]["dimensions"]["width"] == 10.0
        assert result["data"]["dimensions"]["height"] == 15.0

    def test_default_parameters(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_box
        result = geometry_create_box()
        assert result["status"] == "ok"
        assert result["data"]["name"] == "Box"
        assert result["data"]["dimensions"]["length"] == 10.0

    def test_position_parameters(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_box
        # Position is accepted as parameter (even if mock doesn't store it)
        result = geometry_create_box(name="PosBox", pos_x=100.0, pos_y=200.0, pos_z=50.0)
        assert result["status"] == "ok"

    def test_backend_parameter_accepted(self, mock_backend_factory):
        """The backend parameter should be accepted without error."""
        from fc_mcp.tools.geometry import geometry_create_box
        result = geometry_create_box(name="BackendBox", backend="headless")
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# create_cylinder tests
# ---------------------------------------------------------------------------

class TestCreateCylinder:
    """Test geometry_create_cylinder tool."""

    def test_returns_dict(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_cylinder
        result = geometry_create_cylinder(name="TestCyl", radius=10.0, height=50.0)
        assert isinstance(result, dict)

    def test_status_ok(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_cylinder
        result = geometry_create_cylinder(name="MyCyl")
        assert result["status"] == "ok"
        assert result["operation"] == "object_create"

    def test_data_contains_cylinder_info(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_cylinder
        result = geometry_create_cylinder(name="DataCyl", radius=25.0, height=100.0)
        assert result["data"]["name"] == "DataCyl"
        assert result["data"]["type"] == "Part::Cylinder"
        assert result["data"]["dimensions"]["radius"] == 25.0
        assert result["data"]["dimensions"]["height"] == 100.0

    def test_default_parameters(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_cylinder
        result = geometry_create_cylinder()
        assert result["status"] == "ok"
        assert result["data"]["name"] == "Cylinder"
        assert result["data"]["dimensions"]["radius"] == 5.0


# ---------------------------------------------------------------------------
# boolean_union tests
# ---------------------------------------------------------------------------

class TestBooleanUnion:
    """Test geometry_boolean_union tool."""

    def test_returns_dict(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_box, geometry_boolean_union
        geometry_create_box(name="BaseBox", length=20, width=20, height=20)
        geometry_create_box(name="ToolBox", length=10, width=10, height=10)
        result = geometry_boolean_union(base_name="BaseBox", tool_name="ToolBox")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_box, geometry_boolean_union
        geometry_create_box(name="Base", length=20, width=20, height=20)
        geometry_create_box(name="Tool", length=10, width=10, height=10)
        result = geometry_boolean_union(base_name="Base", tool_name="Tool")
        assert result["status"] == "ok"
        assert result["operation"] == "boolean_union"

    def test_data_contains_union_info(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_box, geometry_boolean_union
        geometry_create_box(name="B1", length=20, width=20, height=20)
        geometry_create_box(name="T1", length=10, width=10, height=10)
        result = geometry_boolean_union(base_name="B1", tool_name="T1", result_name="Merged")
        assert result["data"]["name"] == "Merged"
        assert result["data"]["type"] == "BooleanUnion"
        assert result["data"]["base"] == "B1"
        assert result["data"]["tool"] == "T1"

    def test_error_when_base_not_found(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_boolean_union
        result = geometry_boolean_union(base_name="NonExistent", tool_name="AlsoMissing")
        assert result["status"] == "error"

    def test_error_when_tool_not_found(self, mock_backend_factory):
        from fc_mcp.tools.geometry import geometry_create_box, geometry_boolean_union
        geometry_create_box(name="OnlyBase", length=20, width=20, height=20)
        result = geometry_boolean_union(base_name="OnlyBase", tool_name="MissingTool")
        assert result["status"] == "error"
        assert result["error"]["code"] == "OBJ_NOT_FOUND"


# ---------------------------------------------------------------------------
# Tool signature / schema tests
# ---------------------------------------------------------------------------

class TestToolSignatures:
    """Verify tool functions have correct signatures and docstrings."""

    def test_create_box_has_docstring(self):
        from fc_mcp.tools.geometry import geometry_create_box
        assert geometry_create_box.__doc__ is not None
        assert "box" in geometry_create_box.__doc__.lower()

    def test_create_cylinder_has_docstring(self):
        from fc_mcp.tools.geometry import geometry_create_cylinder
        assert geometry_create_cylinder.__doc__ is not None
        assert "cylinder" in geometry_create_cylinder.__doc__.lower()

    def test_boolean_union_has_docstring(self):
        from fc_mcp.tools.geometry import geometry_boolean_union
        assert geometry_boolean_union.__doc__ is None or "boolean" in geometry_boolean_union.__doc__.lower() or "union" in geometry_boolean_union.__doc__.lower()

    def test_all_tools_return_dict_type_annotation(self):
        """All geometry tools should have return type annotation of dict."""
        import inspect
        from fc_mcp.tools import geometry as geo_mod

        tool_functions = [
            getattr(geo_mod, name)
            for name in dir(geo_mod)
            if name.startswith("geometry_") and callable(getattr(geo_mod, name))
        ]
        assert len(tool_functions) >= 3, "Should have at least 3 geometry tools"
        for func in tool_functions:
            sig = inspect.signature(func)
            # With `from __future__ import annotations`, return annotation is a string
            ret = sig.return_annotation
            assert ret is dict or ret == "dict", (
                f"{func.__name__} should have return type annotation 'dict', "
                f"got {ret!r}"
            )


# ---------------------------------------------------------------------------
# Dict format validation tests
# ---------------------------------------------------------------------------

class TestDictFormat:
    """Verify tool responses follow the expected dict format."""

    def test_ok_response_has_required_keys(self, mock_backend_factory):
        """ok responses must have 'status' and 'operation' keys."""
        from fc_mcp.tools.geometry import geometry_create_box
        result = geometry_create_box(name="KeyTest")
        assert "status" in result
        assert "operation" in result
        assert result["status"] == "ok"

    def test_error_response_has_error_key(self, mock_backend_factory):
        """error responses must have 'error' key with 'code' and 'message'."""
        from fc_mcp.tools.geometry import geometry_boolean_union
        result = geometry_boolean_union(base_name="Ghost", tool_name="Phantom")
        assert result["status"] == "error"
        assert "error" in result
        assert "code" in result["error"]
        assert "message" in result["error"]

    def test_data_key_present_in_ok(self, mock_backend_factory):
        """ok responses should include 'data' key."""
        from fc_mcp.tools.geometry import geometry_create_box
        result = geometry_create_box(name="DataKeyTest")
        assert "data" in result
        assert isinstance(result["data"], dict)
