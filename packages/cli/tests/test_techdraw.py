"""Tests for the ``techdraw`` command group.

Covers techdraw sub-commands: page, view, dimension, annotation, symbol,
export, list, get, section, detail, centerline, hatch, table, delete-view.
Uses MockBackend so no real FreeCAD installation is required.
"""

from __future__ import annotations

import json
import os
import tempfile

from fc_core.types import ToolResponse
from fc_cli.main import cli

from tests.conftest import MockBackend


# -- helpers ------------------------------------------------------------------


def _json_output(result) -> dict:
    """Parse JSON from Click result output."""
    return json.loads(result.output.strip())


def _patch_techdraw_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.techdraw."""
    from unittest.mock import patch
    return patch("fc_cli.commands.techdraw._get_backend", return_value=mock)


# -- techdraw page ------------------------------------------------------------


class TestTechdrawPage:
    """Tests for ``fc techdraw page``."""

    def test_page_default(self, mock_backend: MockBackend, runner):
        """Create a page with default parameters."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, ["techdraw", "page"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_page_custom_name(self, mock_backend: MockBackend, runner):
        """Create a page with custom name and format."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "page", "-n", "MyPage", "--format", "A4",
            ])
        assert result.exit_code == 0

    def test_page_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw page."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "techdraw", "page"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_page_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called."""
        with _patch_techdraw_backend(mock_backend):
            runner.invoke(cli, ["techdraw", "page"])
        assert mock_backend.disconnected is True


# -- techdraw view ------------------------------------------------------------


class TestTechdrawView:
    """Tests for ``fc techdraw view``."""

    def test_view_basic(self, mock_backend: MockBackend, runner):
        """Add a view to a page."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "view", "-p", "Page", "-s", "Box",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_view_custom_direction(self, mock_backend: MockBackend, runner):
        """Add a view with custom direction and scale."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "view", "-p", "Page", "-s", "Box",
                "-d", "1,0,0", "--scale", "2.0",
            ])
        assert result.exit_code == 0

    def test_view_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw view."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "view", "-p", "Page", "-s", "Box",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_view_missing_args(self, runner):
        """View without required args should fail."""
        result = runner.invoke(cli, ["techdraw", "view"])
        assert result.exit_code != 0


# -- techdraw dimension -------------------------------------------------------


class TestTechdrawDimension:
    """Tests for ``fc techdraw dimension``."""

    def test_dimension_basic(self, mock_backend: MockBackend, runner):
        """Add a distance dimension."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "dimension", "-v", "MyView",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_dimension_radius(self, mock_backend: MockBackend, runner):
        """Add a radius dimension."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "dimension", "-v", "MyView", "--type", "radius",
            ])
        assert result.exit_code == 0

    def test_dimension_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw dimension."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "dimension", "-v", "MyView",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_dimension_missing_view(self, runner):
        """Dimension without --view should fail."""
        result = runner.invoke(cli, ["techdraw", "dimension"])
        assert result.exit_code != 0


# -- techdraw annotation ------------------------------------------------------


class TestTechdrawAnnotation:
    """Tests for ``fc techdraw annotation``."""

    def test_annotation_basic(self, mock_backend: MockBackend, runner):
        """Add an annotation to a page."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "annotation", "-p", "Page", "-t", "Note text",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_annotation_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw annotation."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "annotation", "-p", "Page", "-t", "Note",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- techdraw symbol ----------------------------------------------------------


class TestTechdrawSymbol:
    """Tests for ``fc techdraw symbol``."""

    def test_symbol_basic(self, mock_backend: MockBackend, runner):
        """Add a symbol to a page."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "symbol", "-p", "Page", "-s", "symbol.svg",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_symbol_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw symbol."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "symbol", "-p", "Page", "-s", "sym.svg",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- techdraw export ----------------------------------------------------------


class TestTechdrawExport:
    """Tests for ``fc techdraw export``."""

    def test_export_basic(self, mock_backend: MockBackend, runner):
        """Export a page to SVG."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "export", "MyPage", "-o", "output.svg",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_export_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw export."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "export", "MyPage", "-o", "output.svg",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_export_missing_output(self, runner):
        """Export without --output should fail."""
        result = runner.invoke(cli, ["techdraw", "export", "MyPage"])
        assert result.exit_code != 0

    def test_export_invalid_format(self, mock_backend: MockBackend, runner):
        """Export with unrecognized extension should error."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "export", "MyPage", "-o", "output.xyz",
            ])
        # _output.error() calls sys.exit(1) when not in repl mode
        assert result.exit_code != 0
        data = _json_output(result)
        assert data["status"] == "error"


# -- techdraw list ------------------------------------------------------------


class TestTechdrawList:
    """Tests for ``fc techdraw list``."""

    def test_list_basic(self, mock_backend: MockBackend, runner):
        """List all TechDraw pages."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, ["techdraw", "list"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_list_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw list."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "techdraw", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- techdraw get -------------------------------------------------------------


class TestTechdrawGet:
    """Tests for ``fc techdraw get``."""

    def test_get_basic(self, mock_backend: MockBackend, runner):
        """Get page details."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, ["techdraw", "get", "MyPage"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_get_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw get."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "techdraw", "get", "MyPage"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_get_missing_name(self, runner):
        """Get without name argument should fail."""
        result = runner.invoke(cli, ["techdraw", "get"])
        assert result.exit_code != 0


# -- techdraw section ---------------------------------------------------------


class TestTechdrawSection:
    """Tests for ``fc techdraw section``."""

    def test_section_basic(self, mock_backend: MockBackend, runner):
        """Create a section view."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "section", "-p", "Page", "-s", "MainView",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_section_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw section."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "section", "-p", "Page", "-s", "MainView",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- techdraw detail ----------------------------------------------------------


class TestTechdrawDetail:
    """Tests for ``fc techdraw detail``."""

    def test_detail_basic(self, mock_backend: MockBackend, runner):
        """Create a detail view."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "detail", "-p", "Page", "-s", "MainView",
                "--center", "10,10,0",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_detail_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw detail."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "detail", "-p", "Page", "-s", "MainView",
                "--center", "10,10,0",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- techdraw centerline ------------------------------------------------------


class TestTechdrawCenterline:
    """Tests for ``fc techdraw centerline``."""

    def test_centerline_basic(self, mock_backend: MockBackend, runner):
        """Add centerlines to a view."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "centerline", "-v", "MyView", "-e", "0,1",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_centerline_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw centerline."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "centerline", "-v", "MyView", "-e", "0",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- techdraw hatch -----------------------------------------------------------


class TestTechdrawHatch:
    """Tests for ``fc techdraw hatch``."""

    def test_hatch_basic(self, mock_backend: MockBackend, runner):
        """Add hatch to a view."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "hatch", "-v", "MyView",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_hatch_custom_pattern(self, mock_backend: MockBackend, runner):
        """Add hatch with custom pattern."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "hatch", "-v", "MyView", "--pattern", "ANSI32",
            ])
        assert result.exit_code == 0

    def test_hatch_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw hatch."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "hatch", "-v", "MyView",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- techdraw table -----------------------------------------------------------


class TestTechdrawTable:
    """Tests for ``fc techdraw table``."""

    def test_table_basic(self, mock_backend: MockBackend, runner):
        """Create a BOM table."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "techdraw", "table", "-p", "Page",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_table_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw table."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "table", "-p", "Page",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- techdraw delete-view -----------------------------------------------------


class TestTechdrawDeleteView:
    """Tests for ``fc techdraw delete-view``."""

    def test_delete_view_basic(self, mock_backend: MockBackend, runner):
        """Delete a view."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, ["techdraw", "delete-view", "MyView"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_delete_view_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for techdraw delete-view."""
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "delete-view", "MyView",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- error handling -----------------------------------------------------------


class TestTechdrawErrors:
    """Tests for error handling in techdraw commands."""

    def test_page_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on page creation, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "PAGE_FAILED", "Simulated failure"),
        )
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "techdraw", "page"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"

    def test_view_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on view, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "VIEW_FAILED", "Simulated failure"),
        )
        with _patch_techdraw_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "techdraw", "view", "-p", "Page", "-s", "Box",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"
