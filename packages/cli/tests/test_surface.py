"""Tests for the ``surface`` command group.

Covers surface sub-commands: loft, sweep, fill, pipe, offset, thicken, flatten,
sew, list, extrude, revolve, ruled, curvature.
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


def _patch_surface_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.surface."""
    from unittest.mock import patch
    return patch("fc_cli.commands.surface._get_backend", return_value=mock)


# -- surface loft -------------------------------------------------------------


class TestSurfaceLoft:
    """Tests for ``fc surface loft``."""

    def test_loft_basic(self, mock_backend: MockBackend, runner):
        """Create a loft with required profiles."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "loft", "-p", "Sketch1;Sketch2",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_loft_solid(self, mock_backend: MockBackend, runner):
        """Create a solid loft."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "loft", "-p", "S1;S2", "--solid",
            ])
        assert result.exit_code == 0

    def test_loft_ruled(self, mock_backend: MockBackend, runner):
        """Create a ruled loft."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "loft", "-p", "S1;S2", "--ruled",
            ])
        assert result.exit_code == 0

    def test_loft_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface loft."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "loft", "-p", "S1;S2",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_loft_with_name(self, mock_backend: MockBackend, runner):
        """Create a loft with custom name."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "loft", "-p", "S1;S2", "-n", "MyLoft",
            ])
        assert result.exit_code == 0

    def test_loft_missing_profiles(self, runner):
        """Loft without --profiles should fail."""
        result = runner.invoke(cli, ["surface", "loft"])
        assert result.exit_code != 0


# -- surface sweep ------------------------------------------------------------


class TestSurfaceSweep:
    """Tests for ``fc surface sweep``."""

    def test_sweep_basic(self, mock_backend: MockBackend, runner):
        """Create a sweep with profile and path."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "sweep", "-p", "Circle", "--path", "Line",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_sweep_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface sweep."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "sweep", "-p", "Circle", "--path", "Line",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_sweep_missing_args(self, runner):
        """Sweep without required args should fail."""
        result = runner.invoke(cli, ["surface", "sweep"])
        assert result.exit_code != 0


# -- surface fill -------------------------------------------------------------


class TestSurfaceFill:
    """Tests for ``fc surface fill``."""

    def test_fill_basic(self, mock_backend: MockBackend, runner):
        """Fill a boundary with a surface."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "fill", "-e", "Box.Edge1;Box.Edge2",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_fill_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface fill."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "fill", "-e", "Box.Edge1",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_fill_missing_edges(self, runner):
        """Fill without --edges should fail."""
        result = runner.invoke(cli, ["surface", "fill"])
        assert result.exit_code != 0


# -- surface pipe -------------------------------------------------------------


class TestSurfacePipe:
    """Tests for ``fc surface pipe``."""

    def test_pipe_basic(self, mock_backend: MockBackend, runner):
        """Create a pipe surface."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, ["surface", "pipe", "-p", "PathObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_pipe_custom_radius(self, mock_backend: MockBackend, runner):
        """Create a pipe with custom radius."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "pipe", "-p", "PathObj", "-r", "5.0",
            ])
        assert result.exit_code == 0

    def test_pipe_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface pipe."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "pipe", "-p", "PathObj",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- surface offset -----------------------------------------------------------


class TestSurfaceOffset:
    """Tests for ``fc surface offset``."""

    def test_offset_basic(self, mock_backend: MockBackend, runner):
        """Create an offset surface."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, ["surface", "offset", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_offset_custom_distance(self, mock_backend: MockBackend, runner):
        """Create an offset with custom distance."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "offset", "MyObj", "-d", "3.0",
            ])
        assert result.exit_code == 0

    def test_offset_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface offset."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "offset", "MyObj",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- surface thicken ----------------------------------------------------------


class TestSurfaceThicken:
    """Tests for ``fc surface thicken``."""

    def test_thicken_basic(self, mock_backend: MockBackend, runner):
        """Thicken a surface."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, ["surface", "thicken", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_thicken_custom_thickness(self, mock_backend: MockBackend, runner):
        """Thicken with custom thickness."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "thicken", "MyObj", "-t", "2.5",
            ])
        assert result.exit_code == 0

    def test_thicken_single_direction(self, mock_backend: MockBackend, runner):
        """Thicken in single direction."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "thicken", "MyObj", "--direction", "single",
            ])
        assert result.exit_code == 0

    def test_thicken_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface thicken."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "thicken", "MyObj",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- surface flatten ----------------------------------------------------------


class TestSurfaceFlatten:
    """Tests for ``fc surface flatten``."""

    def test_flatten_basic(self, mock_backend: MockBackend, runner):
        """Flatten a surface."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, ["surface", "flatten", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_flatten_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface flatten."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "flatten", "MyObj",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- surface sew --------------------------------------------------------------


class TestSurfaceSew:
    """Tests for ``fc surface sew``."""

    def test_sew_basic(self, mock_backend: MockBackend, runner):
        """Sew surfaces together."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "sew", "-o", "Obj1;Obj2",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_sew_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface sew."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "sew", "-o", "Obj1;Obj2",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_sew_missing_objects(self, runner):
        """Sew without --objects should fail."""
        result = runner.invoke(cli, ["surface", "sew"])
        assert result.exit_code != 0


# -- surface list -------------------------------------------------------------


class TestSurfaceList:
    """Tests for ``fc surface list``."""

    def test_list_basic(self, mock_backend: MockBackend, runner):
        """List all surface objects."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, ["surface", "list"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_list_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface list."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "surface", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- surface extrude ----------------------------------------------------------


class TestSurfaceExtrude:
    """Tests for ``fc surface extrude``."""

    def test_extrude_basic(self, mock_backend: MockBackend, runner):
        """Extrude a face or wire."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, ["surface", "extrude", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_extrude_custom_direction(self, mock_backend: MockBackend, runner):
        """Extrude with custom direction."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "extrude", "MyObj", "-d", "0,0,20",
            ])
        assert result.exit_code == 0

    def test_extrude_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface extrude."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "extrude", "MyObj",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- surface revolve ----------------------------------------------------------


class TestSurfaceRevolve:
    """Tests for ``fc surface revolve``."""

    def test_revolve_basic(self, mock_backend: MockBackend, runner):
        """Revolve a profile around an axis."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, ["surface", "revolve", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_revolve_custom_angle(self, mock_backend: MockBackend, runner):
        """Revolve with custom angle."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "revolve", "MyObj", "--angle", "180",
            ])
        assert result.exit_code == 0

    def test_revolve_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface revolve."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "revolve", "MyObj",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- surface ruled ------------------------------------------------------------


class TestSurfaceRuled:
    """Tests for ``fc surface ruled``."""

    def test_ruled_basic(self, mock_backend: MockBackend, runner):
        """Create a ruled surface between two wires."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "surface", "ruled", "Wire1", "Wire2",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_ruled_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for surface ruled."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "ruled", "Wire1", "Wire2",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- surface curvature --------------------------------------------------------


class TestSurfaceCurvature:
    """Tests for ``fc surface curvature``.

    The curvature command previously had a bug in code generation at surface.py:681
    where ``len(faces)-1`` was evaluated at generation time instead of at runtime.
    This has been fixed by escaping the expression with double braces.
    """

    def test_curvature_succeeds(self, mock_backend: MockBackend, runner):
        """Curvature now succeeds after the f-string fix."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, ["surface", "curvature", "MyObj"])
        assert result.exit_code == 0

    def test_curvature_json_output_succeeds(self, mock_backend: MockBackend, runner):
        """--json should also succeed now."""
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "curvature", "MyObj",
            ])
        assert result.exit_code == 0


# -- error handling -----------------------------------------------------------


class TestSurfaceErrors:
    """Tests for error handling in surface commands."""

    def test_loft_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on loft, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "LOFT_FAILED", "Simulated failure"),
        )
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "loft", "-p", "S1;S2",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"

    def test_sweep_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on sweep, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "SWEEP_FAILED", "Simulated failure"),
        )
        with _patch_surface_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "surface", "sweep", "-p", "Circle", "--path", "Line",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"
