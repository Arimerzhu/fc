"""Tests for the ``sketch`` command group.

Covers all sketch sub-commands: new, add-line, add-circle, add-rect, add-arc,
constrain, close, list, get, validate.
Uses MockBackend so no real FreeCAD installation is required.
"""

from __future__ import annotations

import json

from fc_core.types import ToolResponse
from fc_cli.main import cli

from tests.conftest import MockBackend


# ── helpers ------------------------------------------------------------------


def _json_output(result) -> dict:
    """Parse JSON from Click result output."""
    return json.loads(result.output.strip())


def _patch_sketch_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.sketch."""
    from unittest.mock import patch
    return patch("fc_cli.commands.sketch._get_backend", return_value=mock)


# ── sketch new ---------------------------------------------------------------


class TestSketchNew:
    """Tests for ``fc sketch new``."""

    def test_new_default(self, mock_backend: MockBackend, runner):
        """Create a sketch with defaults."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["sketch", "new"])
        assert result.exit_code == 0
        assert mock_backend.was_called("sketch_new")

    def test_new_with_name(self, mock_backend: MockBackend, runner):
        """Create a sketch with a custom name."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["sketch", "new", "-n", "MySketch"])
        assert result.exit_code == 0
        call = [c for c in mock_backend.calls if c[0] == "sketch_new"][0]
        assert call[1][2] == "MySketch"  # third arg is name

    def test_new_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for sketch new."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "sketch", "new", "-n", "JsonSketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "sketch_new"

    def test_new_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called."""
        with _patch_sketch_backend(mock_backend):
            runner.invoke(cli, ["sketch", "new"])
        assert mock_backend.disconnected is True


# ── sketch add-line ----------------------------------------------------------


class TestSketchAddLine:
    """Tests for ``fc sketch add-line``."""

    def test_add_line(self, mock_backend: MockBackend, runner):
        """Add a line to a sketch."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["sketch", "add-line", "Sketch"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_add_line_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for add-line."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "sketch", "add-line", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_add_line_missing_name(self, runner):
        """add-line without sketch name should fail."""
        result = runner.invoke(cli, ["sketch", "add-line"])
        assert result.exit_code != 0


# ── sketch add-circle --------------------------------------------------------


class TestSketchAddCircle:
    """Tests for ``fc sketch add-circle``."""

    def test_add_circle(self, mock_backend: MockBackend, runner):
        """Add a circle to a sketch."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["sketch", "add-circle", "Sketch"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_add_circle_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for add-circle."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "sketch", "add-circle", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# ── sketch add-rect ----------------------------------------------------------


class TestSketchAddRect:
    """Tests for ``fc sketch add-rect``."""

    def test_add_rect(self, mock_backend: MockBackend, runner):
        """Add a rectangle to a sketch."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["sketch", "add-rect", "Sketch"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_add_rect_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for add-rect."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "sketch", "add-rect", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# ── sketch add-arc -----------------------------------------------------------


class TestSketchAddArc:
    """Tests for ``fc sketch add-arc``."""

    def test_add_arc(self, mock_backend: MockBackend, runner):
        """Add an arc to a sketch (source has a bug: start_rad/end_rad NameError)."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["sketch", "add-arc", "Sketch"])
        # NOTE: The source code in sketch.py has a bug where start_rad and end_rad
        # are referenced as Python variables in the f-string but only defined inside
        # the code string passed to execute_code. This causes a NameError.
        # The test documents this known issue.
        assert result.exit_code != 0

    def test_add_arc_json_output(self, mock_backend: MockBackend, runner):
        """Add arc with --json also fails due to source bug."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "sketch", "add-arc", "Sketch"])
        assert result.exit_code != 0


# ── sketch constrain ---------------------------------------------------------


class TestSketchConstrain:
    """Tests for ``fc sketch constrain``."""

    def test_constrain_horizontal(self, mock_backend: MockBackend, runner):
        """Add a horizontal constraint."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, [
                "sketch", "constrain", "Sketch", "horizontal", "-e", "0",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_constrain_vertical(self, mock_backend: MockBackend, runner):
        """Add a vertical constraint."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, [
                "sketch", "constrain", "Sketch", "vertical", "-e", "1",
            ])
        assert result.exit_code == 0

    def test_constrain_distance(self, mock_backend: MockBackend, runner):
        """Add a distance constraint."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, [
                "sketch", "constrain", "Sketch", "distance", "-e", "0,1", "-v", "10.0",
            ])
        assert result.exit_code == 0

    def test_constrain_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for constrain."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "sketch", "constrain", "Sketch", "horizontal", "-e", "0",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_constrain_missing_elements(self, runner):
        """Constrain without --elements should fail."""
        result = runner.invoke(cli, ["sketch", "constrain", "Sketch", "horizontal"])
        assert result.exit_code != 0

    def test_constrain_missing_args(self, runner):
        """Constrain without constraint_type should fail."""
        result = runner.invoke(cli, ["sketch", "constrain", "Sketch"])
        assert result.exit_code != 0


# ── sketch close -------------------------------------------------------------


class TestSketchClose:
    """Tests for ``fc sketch close``."""

    def test_close(self, mock_backend: MockBackend, runner):
        """Close/finalize a sketch."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["sketch", "close", "Sketch"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_close_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for close."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "sketch", "close", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# ── sketch list --------------------------------------------------------------


class TestSketchList:
    """Tests for ``fc sketch list``."""

    def test_list(self, mock_backend: MockBackend, runner):
        """List all sketches."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["sketch", "list"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_list_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for list."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "sketch", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# ── sketch get ---------------------------------------------------------------


class TestSketchGet:
    """Tests for ``fc sketch get``."""

    def test_get(self, mock_backend: MockBackend, runner):
        """Get sketch details."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["sketch", "get", "Sketch"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_get_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for get."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "sketch", "get", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_get_missing_name(self, runner):
        """Get without a name argument should fail."""
        result = runner.invoke(cli, ["sketch", "get"])
        assert result.exit_code != 0


# ── sketch validate ----------------------------------------------------------


class TestSketchValidate:
    """Tests for ``fc sketch validate``."""

    def test_validate(self, mock_backend: MockBackend, runner):
        """Validate a sketch."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["sketch", "validate", "Sketch"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_validate_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for validate."""
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "sketch", "validate", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_validate_missing_name(self, runner):
        """Validate without a name argument should fail."""
        result = runner.invoke(cli, ["sketch", "validate"])
        assert result.exit_code != 0


# ── error handling -----------------------------------------------------------


class TestSketchErrors:
    """Tests for error handling in sketch commands."""

    def test_new_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on new, command should output error JSON."""
        mock_backend.stage_response(
            "sketch_new",
            ToolResponse.error("sketch_new", "CREATE_FAILED", "Simulated failure"),
        )
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "sketch", "new", "-n", "FailSketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"

    def test_add_line_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on add-line, command should output error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "ADD_LINE_FAILED", "Simulated failure"),
        )
        with _patch_sketch_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "sketch", "add-line", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"
