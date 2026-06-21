"""Tests for the ``material`` command group.

Covers material sub-commands: list, show, assign, create, edit, remove,
library, export, import.
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


def _patch_material_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.material."""
    from unittest.mock import patch
    return patch("fc_cli.commands.material._get_backend", return_value=mock)


# -- material list ------------------------------------------------------------


class TestMaterialList:
    """Tests for ``fc material list``."""

    def test_list_basic(self, mock_backend: MockBackend, runner):
        """List all materials."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, ["material", "list"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_list_with_library(self, mock_backend: MockBackend, runner):
        """List materials filtered by library."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, ["material", "list", "-l", "Steel"])
        assert result.exit_code == 0

    def test_list_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for material list."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "material", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_list_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called."""
        with _patch_material_backend(mock_backend):
            runner.invoke(cli, ["material", "list"])
        assert mock_backend.disconnected is True


# -- material show ------------------------------------------------------------


class TestMaterialShow:
    """Tests for ``fc material show``."""

    def test_show_basic(self, mock_backend: MockBackend, runner):
        """Show material properties."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, ["material", "show", "Steel"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_show_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for material show."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "material", "show", "Steel"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_show_missing_name(self, runner):
        """Show without name argument should fail."""
        result = runner.invoke(cli, ["material", "show"])
        assert result.exit_code != 0


# -- material assign ----------------------------------------------------------


class TestMaterialAssign:
    """Tests for ``fc material assign``.

    The assign command previously had a bug -- Click option ``--object`` mapped to
    keyword ``object`` but the function signature used ``obj``.
    This has been fixed by adding an explicit Click parameter name mapping.
    """

    def test_assign_succeeds(self, mock_backend: MockBackend, runner):
        """Assign succeeds after the parameter name fix."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, [
                "material", "assign", "-o", "Box", "-m", "Steel",
            ])
        assert result.exit_code == 0

    def test_assign_json_output_succeeds(self, mock_backend: MockBackend, runner):
        """--json should also succeed now."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "material", "assign", "-o", "Box", "-m", "Steel",
            ])
        assert result.exit_code == 0


# -- material create ----------------------------------------------------------


class TestMaterialCreate:
    """Tests for ``fc material create``."""

    def test_create_basic(self, mock_backend: MockBackend, runner):
        """Create a custom material."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, [
                "material", "create", "-n", "MySteel",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_create_with_properties(self, mock_backend: MockBackend, runner):
        """Create a material with properties."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, [
                "material", "create", "-n", "MySteel",
                "--density", "7850", "--youngs-modulus", "200e9",
            ])
        assert result.exit_code == 0

    def test_create_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for material create."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "material", "create", "-n", "MySteel",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- material edit ------------------------------------------------------------


class TestMaterialEdit:
    """Tests for ``fc material edit``."""

    def test_edit_basic(self, mock_backend: MockBackend, runner):
        """Edit material properties."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, [
                "material", "edit", "MySteel", "-p", "Density=8000",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_edit_multiple_properties(self, mock_backend: MockBackend, runner):
        """Edit multiple material properties."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, [
                "material", "edit", "MySteel",
                "-p", "Density=8000", "-p", "Color=1,0,0",
            ])
        assert result.exit_code == 0

    def test_edit_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for material edit."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "material", "edit", "MySteel", "-p", "Density=8000",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- material remove ----------------------------------------------------------


class TestMaterialRemove:
    """Tests for ``fc material remove``."""

    def test_remove_basic(self, mock_backend: MockBackend, runner):
        """Remove a material."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, ["material", "remove", "MySteel"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_remove_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for material remove."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "material", "remove", "MySteel"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- material library ---------------------------------------------------------


class TestMaterialLibrary:
    """Tests for ``fc material library``."""

    def test_library_basic(self, mock_backend: MockBackend, runner):
        """List material libraries."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, ["material", "library"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_library_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for material library."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "material", "library"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- material export ----------------------------------------------------------


class TestMaterialExport:
    """Tests for ``fc material export``."""

    def test_export_basic(self, mock_backend: MockBackend, runner):
        """Export a material card."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, [
                "material", "export", "MySteel", "-o", "steel.json",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_export_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for material export."""
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "material", "export", "MySteel", "-o", "steel.json",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_export_existing_no_overwrite(self, mock_backend: MockBackend, runner):
        """Export to existing file without --overwrite should error."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_material_backend(mock_backend):
                result = runner.invoke(cli, [
                    "--json", "material", "export", "MySteel", "-o", tmp_path,
                ])
            # _output.error() calls sys.exit(1) when not in repl mode
            assert result.exit_code != 0
        finally:
            os.unlink(tmp_path)

    def test_export_missing_output(self, runner):
        """Export without --output should fail."""
        result = runner.invoke(cli, ["material", "export", "MySteel"])
        assert result.exit_code != 0


# -- material import ----------------------------------------------------------


class TestMaterialImport:
    """Tests for ``fc material import``."""

    def test_import_basic(self, mock_backend: MockBackend, runner):
        """Import a material card."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write('{"name": "TestMat"}')
            tmp_path = f.name
        try:
            with _patch_material_backend(mock_backend):
                result = runner.invoke(cli, ["material", "import", tmp_path])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp_path)

    def test_import_with_name(self, mock_backend: MockBackend, runner):
        """Import a material card with name override."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write('{"name": "TestMat"}')
            tmp_path = f.name
        try:
            with _patch_material_backend(mock_backend):
                result = runner.invoke(cli, [
                    "material", "import", tmp_path, "-n", "CustomName",
                ])
            assert result.exit_code == 0
        finally:
            os.unlink(tmp_path)

    def test_import_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for material import."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write('{"name": "TestMat"}')
            tmp_path = f.name
        try:
            with _patch_material_backend(mock_backend):
                result = runner.invoke(cli, [
                    "--json", "material", "import", tmp_path,
                ])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            os.unlink(tmp_path)

    def test_import_nonexistent_file(self, runner):
        """Import from non-existent file should fail."""
        result = runner.invoke(cli, ["material", "import", "no_such_file.json"])
        assert result.exit_code != 0


# -- error handling -----------------------------------------------------------


class TestMaterialErrors:
    """Tests for error handling in material commands."""

    def test_list_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on list, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "LIST_FAILED", "Simulated failure"),
        )
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "material", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"

    def test_show_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on show, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "NOT_FOUND", "Material not found"),
        )
        with _patch_material_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "material", "show", "NonExistent"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"
