"""Tests for the ``spreadsheet`` command group.

Covers spreadsheet sub-commands: create, set, get, formula, alias, link,
show, list, clear, export, import.
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


def _patch_spreadsheet_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.spreadsheet."""
    from unittest.mock import patch
    return patch("fc_cli.commands.spreadsheet._get_backend", return_value=mock)


# -- spreadsheet create -------------------------------------------------------


class TestSpreadsheetCreate:
    """Tests for ``fc spreadsheet create``."""

    def test_create_default(self, mock_backend: MockBackend, runner):
        """Create a spreadsheet with default name."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, ["spreadsheet", "create"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_create_custom_name(self, mock_backend: MockBackend, runner):
        """Create a spreadsheet with custom name."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, ["spreadsheet", "create", "-n", "MySheet"])
        assert result.exit_code == 0

    def test_create_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for spreadsheet create."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "spreadsheet", "create"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_create_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called."""
        with _patch_spreadsheet_backend(mock_backend):
            runner.invoke(cli, ["spreadsheet", "create"])
        assert mock_backend.disconnected is True


# -- spreadsheet set ----------------------------------------------------------


class TestSpreadsheetSet:
    """Tests for ``fc spreadsheet set``."""

    def test_set_basic(self, mock_backend: MockBackend, runner):
        """Set a cell value."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "spreadsheet", "set", "-s", "Sheet", "-c", "A1", "-v", "42",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_set_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for spreadsheet set."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "spreadsheet", "set", "-s", "Sheet", "-c", "A1", "-v", "100",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_set_missing_args(self, runner):
        """Set without required args should fail."""
        result = runner.invoke(cli, ["spreadsheet", "set"])
        assert result.exit_code != 0


# -- spreadsheet get ----------------------------------------------------------


class TestSpreadsheetGet:
    """Tests for ``fc spreadsheet get``."""

    def test_get_basic(self, mock_backend: MockBackend, runner):
        """Get a cell value."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "spreadsheet", "get", "-s", "Sheet", "-c", "A1",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_get_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for spreadsheet get."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "spreadsheet", "get", "-s", "Sheet", "-c", "A1",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- spreadsheet formula ------------------------------------------------------


class TestSpreadsheetFormula:
    """Tests for ``fc spreadsheet formula``."""

    def test_formula_basic(self, mock_backend: MockBackend, runner):
        """Set a cell formula."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "spreadsheet", "formula", "-s", "Sheet", "-c", "B1", "-f", "=A1*2",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_formula_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for spreadsheet formula."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "spreadsheet", "formula", "-s", "Sheet", "-c", "B1", "-f", "=A1+1",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- spreadsheet alias --------------------------------------------------------


class TestSpreadsheetAlias:
    """Tests for ``fc spreadsheet alias``."""

    def test_alias_basic(self, mock_backend: MockBackend, runner):
        """Set a cell alias."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "spreadsheet", "alias", "-s", "Sheet", "-c", "A1", "-a", "width",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_alias_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for spreadsheet alias."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "spreadsheet", "alias", "-s", "Sheet", "-c", "A1", "-a", "height",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- spreadsheet link ---------------------------------------------------------


class TestSpreadsheetLink:
    """Tests for ``fc spreadsheet link``.

    The link command previously had a bug -- Click option ``--object`` mapped to
    keyword ``object`` but the function signature used ``obj``. Similarly
    ``--property`` mapped to ``property`` but the function used ``prop``.
    This has been fixed by adding explicit Click parameter name mappings.
    """

    def test_link_succeeds(self, mock_backend: MockBackend, runner):
        """Link succeeds after the parameter name fix."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "spreadsheet", "link", "-s", "Sheet", "-c", "A1",
                "-o", "Box", "-p", "Length",
            ])
        assert result.exit_code == 0

    def test_link_json_output_succeeds(self, mock_backend: MockBackend, runner):
        """--json should also succeed now."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "spreadsheet", "link", "-s", "Sheet", "-c", "A1",
                "-o", "Box", "-p", "Length",
            ])
        assert result.exit_code == 0


# -- spreadsheet show ---------------------------------------------------------


class TestSpreadsheetShow:
    """Tests for ``fc spreadsheet show``."""

    def test_show_basic(self, mock_backend: MockBackend, runner):
        """Display spreadsheet contents."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "spreadsheet", "show", "-s", "Sheet",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_show_with_range(self, mock_backend: MockBackend, runner):
        """Display a specific range."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "spreadsheet", "show", "-s", "Sheet", "-r", "A1:D10",
            ])
        assert result.exit_code == 0

    def test_show_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for spreadsheet show."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "spreadsheet", "show", "-s", "Sheet",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- spreadsheet list ---------------------------------------------------------


class TestSpreadsheetList:
    """Tests for ``fc spreadsheet list``."""

    def test_list_basic(self, mock_backend: MockBackend, runner):
        """List all spreadsheets."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, ["spreadsheet", "list"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_list_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for spreadsheet list."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "spreadsheet", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- spreadsheet clear --------------------------------------------------------


class TestSpreadsheetClear:
    """Tests for ``fc spreadsheet clear``."""

    def test_clear_cell(self, mock_backend: MockBackend, runner):
        """Clear a single cell."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "spreadsheet", "clear", "-s", "Sheet", "-c", "A1",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_clear_range(self, mock_backend: MockBackend, runner):
        """Clear a range of cells."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "spreadsheet", "clear", "-s", "Sheet", "-r", "A1:C10",
            ])
        assert result.exit_code == 0

    def test_clear_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for spreadsheet clear."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "spreadsheet", "clear", "-s", "Sheet", "-c", "A1",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_clear_no_cell_or_range(self, mock_backend: MockBackend, runner):
        """Clear without --cell or --range should error."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "spreadsheet", "clear", "-s", "Sheet",
            ])
        # _output.error() calls sys.exit(1) when not in repl mode
        assert result.exit_code != 0


# -- spreadsheet export -------------------------------------------------------


class TestSpreadsheetExport:
    """Tests for ``fc spreadsheet export``."""

    def test_export_basic(self, mock_backend: MockBackend, runner):
        """Export spreadsheet to CSV."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "spreadsheet", "export", "-s", "Sheet", "-o", "output.csv",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_export_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for spreadsheet export."""
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "spreadsheet", "export", "-s", "Sheet", "-o", "output.csv",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_export_existing_no_overwrite(self, mock_backend: MockBackend, runner):
        """Export to existing file without --overwrite should error."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_spreadsheet_backend(mock_backend):
                result = runner.invoke(cli, [
                    "--json", "spreadsheet", "export", "-s", "Sheet", "-o", tmp_path,
                ])
            # _output.error() calls sys.exit(1) when not in repl mode
            assert result.exit_code != 0
        finally:
            os.unlink(tmp_path)


# -- spreadsheet import -------------------------------------------------------


class TestSpreadsheetImport:
    """Tests for ``fc spreadsheet import``."""

    def test_import_basic(self, mock_backend: MockBackend, runner):
        """Import from CSV."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("a,b,c\n1,2,3\n")
            tmp_path = f.name
        try:
            with _patch_spreadsheet_backend(mock_backend):
                result = runner.invoke(cli, [
                    "spreadsheet", "import", "-s", "Sheet", "-i", tmp_path,
                ])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp_path)

    def test_import_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for spreadsheet import."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("x,y\n")
            tmp_path = f.name
        try:
            with _patch_spreadsheet_backend(mock_backend):
                result = runner.invoke(cli, [
                    "--json", "spreadsheet", "import", "-s", "Sheet", "-i", tmp_path,
                ])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            os.unlink(tmp_path)

    def test_import_nonexistent_file(self, runner):
        """Import from non-existent file should fail."""
        result = runner.invoke(cli, [
            "spreadsheet", "import", "-s", "Sheet", "-i", "no_such.csv",
        ])
        assert result.exit_code != 0


# -- error handling -----------------------------------------------------------


class TestSpreadsheetErrors:
    """Tests for error handling in spreadsheet commands."""

    def test_create_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on create, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "CREATE_FAILED", "Simulated failure"),
        )
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "spreadsheet", "create"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"

    def test_set_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on set, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "SET_FAILED", "Simulated failure"),
        )
        with _patch_spreadsheet_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "spreadsheet", "set", "-s", "Sheet", "-c", "A1", "-v", "42",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"
