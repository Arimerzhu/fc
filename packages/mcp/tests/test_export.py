"""Tests for export MCP tools: export_step, export_stl, export_obj, etc."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_export_backend(mock_backend):
    """Patch _get_backend in the export tools module."""
    from unittest.mock import patch

    def _factory(backend_type="headless", **kwargs):
        return mock_backend

    with patch("fc_mcp.tools.export._get_backend", side_effect=_factory):
        yield mock_backend


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------

class TestExportToolRegistration:
    """Verify export tools are properly registered with MCP."""

    EXPECTED_TOOLS = [
        "export_step",
        "export_stl",
        "export_obj",
        "export_brep",
        "export_dxf",
        "export_svg",
        "export_pdf",
        "export_gltf",
        "export_3mf",
        "export_fcstd",
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
# export_step tests
# ---------------------------------------------------------------------------

class TestExportStep:
    """Test export_step tool."""

    def test_returns_dict(self, mock_export_backend):
        from fc_mcp.tools.export import export_step
        result = export_step(file_path="/tmp/model.step")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_export_backend):
        from fc_mcp.tools.export import export_step
        result = export_step(file_path="/tmp/model.step")
        assert result["status"] == "ok"
        assert result["operation"] == "export"

    def test_data_contains_format(self, mock_export_backend):
        from fc_mcp.tools.export import export_step
        result = export_step(file_path="/tmp/model.step")
        assert result["data"]["format"] == "step"

    def test_requires_file_path(self):
        from fc_mcp.tools.export import export_step
        with pytest.raises(TypeError):
            export_step()


# ---------------------------------------------------------------------------
# export_stl tests
# ---------------------------------------------------------------------------

class TestExportStl:
    """Test export_stl tool."""

    def test_returns_dict(self, mock_export_backend):
        from fc_mcp.tools.export import export_stl
        result = export_stl(file_path="/tmp/model.stl")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_export_backend):
        from fc_mcp.tools.export import export_stl
        result = export_stl(file_path="/tmp/model.stl")
        assert result["status"] == "ok"

    def test_requires_file_path(self):
        from fc_mcp.tools.export import export_stl
        with pytest.raises(TypeError):
            export_stl()

    def test_tolerance_parameter(self, mock_export_backend):
        from fc_mcp.tools.export import export_stl
        result = export_stl(file_path="/tmp/model.stl", tolerance=0.01)
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# export_obj tests
# ---------------------------------------------------------------------------

class TestExportObj:
    """Test export_obj tool."""

    def test_returns_dict(self, mock_export_backend):
        from fc_mcp.tools.export import export_obj
        result = export_obj(file_path="/tmp/model.obj")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_export_backend):
        from fc_mcp.tools.export import export_obj
        result = export_obj(file_path="/tmp/model.obj")
        assert result["status"] == "ok"
        assert result["operation"] == "export"

    def test_data_contains_format(self, mock_export_backend):
        from fc_mcp.tools.export import export_obj
        result = export_obj(file_path="/tmp/model.obj")
        assert result["data"]["format"] == "obj"


# ---------------------------------------------------------------------------
# export_brep tests
# ---------------------------------------------------------------------------

class TestExportBrep:
    """Test export_brep tool."""

    def test_returns_dict(self, mock_export_backend):
        from fc_mcp.tools.export import export_brep
        result = export_brep(file_path="/tmp/model.brep")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_export_backend):
        from fc_mcp.tools.export import export_brep
        result = export_brep(file_path="/tmp/model.brep")
        assert result["status"] == "ok"
        assert result["operation"] == "export"

    def test_data_contains_format(self, mock_export_backend):
        from fc_mcp.tools.export import export_brep
        result = export_brep(file_path="/tmp/model.brep")
        assert result["data"]["format"] == "brep"


# ---------------------------------------------------------------------------
# export_dxf tests
# ---------------------------------------------------------------------------

class TestExportDxf:
    """Test export_dxf tool."""

    def test_returns_dict(self, mock_export_backend):
        from fc_mcp.tools.export import export_dxf
        result = export_dxf(file_path="/tmp/model.dxf")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_export_backend):
        from fc_mcp.tools.export import export_dxf
        result = export_dxf(file_path="/tmp/model.dxf")
        assert result["status"] == "ok"
        assert result["operation"] == "export"

    def test_data_contains_format(self, mock_export_backend):
        from fc_mcp.tools.export import export_dxf
        result = export_dxf(file_path="/tmp/model.dxf")
        assert result["data"]["format"] == "dxf"


# ---------------------------------------------------------------------------
# export_svg tests
# ---------------------------------------------------------------------------

class TestExportSvg:
    """Test export_svg tool."""

    def test_returns_dict(self, mock_export_backend):
        from fc_mcp.tools.export import export_svg
        result = export_svg(file_path="/tmp/model.svg")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_export_backend):
        from fc_mcp.tools.export import export_svg
        result = export_svg(file_path="/tmp/model.svg")
        assert result["status"] == "ok"
        assert result["operation"] == "export"

    def test_data_contains_format(self, mock_export_backend):
        from fc_mcp.tools.export import export_svg
        result = export_svg(file_path="/tmp/model.svg")
        assert result["data"]["format"] == "svg"


# ---------------------------------------------------------------------------
# export_pdf tests
# ---------------------------------------------------------------------------

class TestExportPdf:
    """Test export_pdf tool."""

    def test_returns_dict(self, mock_export_backend):
        from fc_mcp.tools.export import export_pdf
        result = export_pdf(file_path="/tmp/model.pdf")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_export_backend):
        from fc_mcp.tools.export import export_pdf
        result = export_pdf(file_path="/tmp/model.pdf")
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# export_gltf tests
# ---------------------------------------------------------------------------

class TestExportGltf:
    """Test export_gltf tool."""

    def test_returns_dict(self, mock_export_backend):
        from fc_mcp.tools.export import export_gltf
        result = export_gltf(file_path="/tmp/model.gltf")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_export_backend):
        from fc_mcp.tools.export import export_gltf
        result = export_gltf(file_path="/tmp/model.gltf")
        assert result["status"] == "ok"
        assert result["operation"] == "export"

    def test_data_contains_format(self, mock_export_backend):
        from fc_mcp.tools.export import export_gltf
        result = export_gltf(file_path="/tmp/model.gltf")
        assert result["data"]["format"] == "gltf"


# ---------------------------------------------------------------------------
# export_3mf tests
# ---------------------------------------------------------------------------

class TestExport3mf:
    """Test export_3mf tool."""

    def test_returns_dict(self, mock_export_backend):
        from fc_mcp.tools.export import export_3mf
        result = export_3mf(file_path="/tmp/model.3mf")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_export_backend):
        from fc_mcp.tools.export import export_3mf
        result = export_3mf(file_path="/tmp/model.3mf")
        assert result["status"] == "ok"
        assert result["operation"] == "export"

    def test_data_contains_format(self, mock_export_backend):
        from fc_mcp.tools.export import export_3mf
        result = export_3mf(file_path="/tmp/model.3mf")
        assert result["data"]["format"] == "3mf"


# ---------------------------------------------------------------------------
# export_fcstd tests
# ---------------------------------------------------------------------------

class TestExportFcstd:
    """Test export_fcstd tool."""

    def test_returns_dict(self, mock_export_backend):
        from fc_mcp.tools.export import export_fcstd
        result = export_fcstd(file_path="/tmp/model.FCStd")
        assert isinstance(result, dict)

    def test_status_ok(self, mock_export_backend):
        from fc_mcp.tools.export import export_fcstd
        result = export_fcstd(file_path="/tmp/model.FCStd")
        assert result["status"] == "ok"
        assert result["operation"] == "document_save"


# ---------------------------------------------------------------------------
# Dict format validation
# ---------------------------------------------------------------------------

class TestDictFormat:
    """Verify export tool responses follow the expected dict format."""

    def test_ok_response_has_required_keys(self, mock_export_backend):
        from fc_mcp.tools.export import export_step
        result = export_step(file_path="/tmp/test.step")
        assert "status" in result
        assert "operation" in result
        assert result["status"] == "ok"

    def test_data_key_present_in_ok(self, mock_export_backend):
        from fc_mcp.tools.export import export_step
        result = export_step(file_path="/tmp/test.step")
        assert "data" in result
        assert isinstance(result["data"], dict)

    def test_export_data_has_format(self, mock_export_backend):
        """Export responses should include format in data."""
        from fc_mcp.tools.export import export_step
        result = export_step(file_path="/tmp/test.step")
        assert "format" in result["data"]


# ---------------------------------------------------------------------------
# Tool signature / schema tests
# ---------------------------------------------------------------------------

class TestToolSignatures:
    """Verify export tool functions have correct signatures."""

    def test_export_step_has_docstring(self):
        from fc_mcp.tools.export import export_step
        assert export_step.__doc__ is not None
        assert "step" in export_step.__doc__.lower()

    def test_export_stl_has_docstring(self):
        from fc_mcp.tools.export import export_stl
        assert export_stl.__doc__ is not None
        assert "stl" in export_stl.__doc__.lower()

    def test_all_tools_return_dict(self):
        import inspect
        from fc_mcp.tools import export as export_mod

        tool_functions = [
            getattr(export_mod, name)
            for name in dir(export_mod)
            if name.startswith("export_") and callable(getattr(export_mod, name))
        ]
        assert len(tool_functions) >= 3
        for func in tool_functions:
            sig = inspect.signature(func)
            ret = sig.return_annotation
            assert ret is dict or ret == "dict", (
                f"{func.__name__} should return dict, got {ret!r}"
            )
