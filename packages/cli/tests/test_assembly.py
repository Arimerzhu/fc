"""Tests for the ``assembly`` command group.

Covers assembly sub-commands: create, add, remove, constraint, solve,
explode, animate, list, ground, show, interference, bom.
Uses MockBackend so no real FreeCAD installation is required.
"""

from __future__ import annotations

import json

from fc_core.types import ToolResponse
from fc_cli.main import cli

from tests.conftest import MockBackend


# -- helpers ------------------------------------------------------------------


def _json_output(result) -> dict:
    """Parse JSON from Click result output."""
    return json.loads(result.output.strip())


def _patch_assembly_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.assembly."""
    from unittest.mock import patch
    return patch("fc_cli.commands.assembly._get_backend", return_value=mock)


# -- assembly create ----------------------------------------------------------


class TestAssemblyCreate:
    """Tests for ``fc assembly create``."""

    def test_create_default(self, mock_backend: MockBackend, runner):
        """Create an assembly with default parameters."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["assembly", "create"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_create_custom_name(self, mock_backend: MockBackend, runner):
        """Create an assembly with custom name and type."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "assembly", "create", "-n", "MyAssembly", "--type", "a4",
            ])
        assert result.exit_code == 0

    def test_create_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly create."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "assembly", "create"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_create_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called."""
        with _patch_assembly_backend(mock_backend):
            runner.invoke(cli, ["assembly", "create"])
        assert mock_backend.disconnected is True


# -- assembly add -------------------------------------------------------------


class TestAssemblyAdd:
    """Tests for ``fc assembly add``."""

    def test_add_basic(self, mock_backend: MockBackend, runner):
        """Add a part to the assembly."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "assembly", "add", "-a", "MyAsm", "-o", "Box",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_add_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly add."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "assembly", "add", "-a", "MyAsm", "-o", "Box",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_add_missing_args(self, runner):
        """Add without required args should fail."""
        result = runner.invoke(cli, ["assembly", "add"])
        assert result.exit_code != 0


# -- assembly remove ----------------------------------------------------------


class TestAssemblyRemove:
    """Tests for ``fc assembly remove``."""

    def test_remove_basic(self, mock_backend: MockBackend, runner):
        """Remove a part from the assembly."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "assembly", "remove", "-a", "MyAsm", "-o", "Box",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_remove_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly remove."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "assembly", "remove", "-a", "MyAsm", "-o", "Box",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- assembly constraint ------------------------------------------------------


class TestAssemblyConstraint:
    """Tests for ``fc assembly constraint``."""

    def test_constraint_coincident(self, mock_backend: MockBackend, runner):
        """Add a coincident constraint."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "assembly", "constraint", "-t", "coincident",
                "-o1", "Box", "-o2", "Cylinder",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_constraint_distance(self, mock_backend: MockBackend, runner):
        """Add a distance constraint with value."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "assembly", "constraint", "-t", "distance",
                "-o1", "Box", "-o2", "Cylinder", "--value", "10.0",
            ])
        assert result.exit_code == 0

    def test_constraint_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly constraint."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "assembly", "constraint", "-t", "coincident",
                "-o1", "Box", "-o2", "Cylinder",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_constraint_missing_args(self, runner):
        """Constraint without required args should fail."""
        result = runner.invoke(cli, ["assembly", "constraint"])
        assert result.exit_code != 0

    def test_constraint_invalid_type(self, runner):
        """Constraint with invalid type should fail."""
        result = runner.invoke(cli, [
            "assembly", "constraint", "-t", "invalid", "-o1", "A", "-o2", "B",
        ])
        assert result.exit_code != 0


# -- assembly solve -----------------------------------------------------------


class TestAssemblySolve:
    """Tests for ``fc assembly solve``."""

    def test_solve_basic(self, mock_backend: MockBackend, runner):
        """Solve assembly constraints."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["assembly", "solve"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_solve_with_assembly(self, mock_backend: MockBackend, runner):
        """Solve constraints for a specific assembly."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["assembly", "solve", "-a", "MyAsm"])
        assert result.exit_code == 0

    def test_solve_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly solve."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "assembly", "solve"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- assembly explode ---------------------------------------------------------


class TestAssemblyExplode:
    """Tests for ``fc assembly explode``."""

    def test_explode_basic(self, mock_backend: MockBackend, runner):
        """Create an exploded view."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["assembly", "explode"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_explode_custom(self, mock_backend: MockBackend, runner):
        """Explode with custom factor and direction."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "assembly", "explode", "--factor", "3.0", "--direction", "x",
            ])
        assert result.exit_code == 0

    def test_explode_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly explode."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "assembly", "explode"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- assembly animate ---------------------------------------------------------


class TestAssemblyAnimate:
    """Tests for ``fc assembly animate``."""

    def test_animate_basic(self, mock_backend: MockBackend, runner):
        """Create an animation."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["assembly", "animate"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_animate_custom(self, mock_backend: MockBackend, runner):
        """Animate with custom parameters."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "assembly", "animate", "--start", "0", "--end", "360", "--steps", "60",
            ])
        assert result.exit_code == 0

    def test_animate_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly animate."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "assembly", "animate"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- assembly list ------------------------------------------------------------


class TestAssemblyList:
    """Tests for ``fc assembly list``."""

    def test_list_basic(self, mock_backend: MockBackend, runner):
        """List all parts in assembly."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["assembly", "list"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_list_with_assembly(self, mock_backend: MockBackend, runner):
        """List parts in a specific assembly."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["assembly", "list", "-a", "MyAsm"])
        assert result.exit_code == 0

    def test_list_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly list."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "assembly", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- assembly ground ----------------------------------------------------------


class TestAssemblyGround:
    """Tests for ``fc assembly ground``."""

    def test_ground_basic(self, mock_backend: MockBackend, runner):
        """Ground a part."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "assembly", "ground", "-a", "MyAsm", "-o", "Box",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_ground_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly ground."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "assembly", "ground", "-a", "MyAsm", "-o", "Box",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- assembly show ------------------------------------------------------------


class TestAssemblyShow:
    """Tests for ``fc assembly show``."""

    def test_show_basic(self, mock_backend: MockBackend, runner):
        """Show assembly tree."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["assembly", "show"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_show_with_assembly(self, mock_backend: MockBackend, runner):
        """Show tree of a specific assembly."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["assembly", "show", "-a", "MyAsm"])
        assert result.exit_code == 0

    def test_show_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly show."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "assembly", "show"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- assembly interference ----------------------------------------------------


class TestAssemblyInterference:
    """Tests for ``fc assembly interference``."""

    def test_interference_basic(self, mock_backend: MockBackend, runner):
        """Check interference between all parts."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["assembly", "interference"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_interference_two_objects(self, mock_backend: MockBackend, runner):
        """Check interference between two specific objects."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "assembly", "interference", "-o1", "Box", "-o2", "Cylinder",
            ])
        assert result.exit_code == 0

    def test_interference_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly interference."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "assembly", "interference"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- assembly bom -------------------------------------------------------------


class TestAssemblyBom:
    """Tests for ``fc assembly bom``."""

    def test_bom_basic(self, mock_backend: MockBackend, runner):
        """Generate a BOM."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["assembly", "bom"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_bom_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for assembly bom."""
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "assembly", "bom"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- error handling -----------------------------------------------------------


class TestAssemblyErrors:
    """Tests for error handling in assembly commands."""

    def test_create_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on create, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "CREATE_FAILED", "Simulated failure"),
        )
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "assembly", "create"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"

    def test_constraint_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on constraint, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "CONSTRAINT_FAILED", "Simulated failure"),
        )
        with _patch_assembly_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "assembly", "constraint", "-t", "coincident",
                "-o1", "Box", "-o2", "Cylinder",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"
