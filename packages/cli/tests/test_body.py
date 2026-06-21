"""Tests for the ``body`` command group.

Covers all body sub-commands: new, pad, pocket, fillet, chamfer, revolution,
groove, list, get.
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


def _patch_body_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.body."""
    from unittest.mock import patch
    return patch("fc_cli.commands.body._get_backend", return_value=mock)


# ── body new -----------------------------------------------------------------


class TestBodyNew:
    """Tests for ``fc body new``."""

    def test_new_default(self, mock_backend: MockBackend, runner):
        """Create a body with default name."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["body", "new"])
        assert result.exit_code == 0
        assert mock_backend.was_called("body_new")

    def test_new_custom_name(self, mock_backend: MockBackend, runner):
        """Create a body with a custom name."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["body", "new", "-n", "MyBody"])
        assert result.exit_code == 0
        call = [c for c in mock_backend.calls if c[0] == "body_new"][0]
        assert call[1][0] == "MyBody"

    def test_new_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for body new."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "body", "new", "-n", "JsonBody"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "body_new"

    def test_new_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called."""
        with _patch_body_backend(mock_backend):
            runner.invoke(cli, ["body", "new"])
        assert mock_backend.disconnected is True


# ── body pad -----------------------------------------------------------------


class TestBodyPad:
    """Tests for ``fc body pad``."""

    def test_pad(self, mock_backend: MockBackend, runner):
        """Add a pad feature to a body."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["body", "pad", "Body", "Sketch"])
        assert result.exit_code == 0
        assert mock_backend.was_called("body_pad")

    def test_pad_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for pad."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "body", "pad", "Body", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "body_pad"

    def test_pad_missing_args(self, runner):
        """Pad without required arguments should fail."""
        result = runner.invoke(cli, ["body", "pad", "Body"])
        assert result.exit_code != 0


# ── body pocket --------------------------------------------------------------


class TestBodyPocket:
    """Tests for ``fc body pocket``."""

    def test_pocket(self, mock_backend: MockBackend, runner):
        """Add a pocket feature to a body."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["body", "pocket", "Body", "Sketch"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_pocket_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for pocket."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "body", "pocket", "Body", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_pocket_missing_args(self, runner):
        """Pocket without required arguments should fail."""
        result = runner.invoke(cli, ["body", "pocket", "Body"])
        assert result.exit_code != 0


# ── body fillet --------------------------------------------------------------


class TestBodyFillet:
    """Tests for ``fc body fillet``."""

    def test_fillet(self, mock_backend: MockBackend, runner):
        """Add a fillet feature to a body."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["body", "fillet", "Body"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_fillet_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for fillet."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "body", "fillet", "Body"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_fillet_missing_body(self, runner):
        """Fillet without body name should fail."""
        result = runner.invoke(cli, ["body", "fillet"])
        assert result.exit_code != 0


# ── body chamfer -------------------------------------------------------------


class TestBodyChamfer:
    """Tests for ``fc body chamfer``."""

    def test_chamfer(self, mock_backend: MockBackend, runner):
        """Add a chamfer feature to a body."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["body", "chamfer", "Body"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_chamfer_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for chamfer."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "body", "chamfer", "Body"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# ── body revolution ----------------------------------------------------------


class TestBodyRevolution:
    """Tests for ``fc body revolution``."""

    def test_revolution(self, mock_backend: MockBackend, runner):
        """Add a revolution feature to a body."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["body", "revolution", "Body", "Sketch"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_revolution_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for revolution."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "body", "revolution", "Body", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_revolution_missing_args(self, runner):
        """Revolution without required arguments should fail."""
        result = runner.invoke(cli, ["body", "revolution", "Body"])
        assert result.exit_code != 0


# ── body groove --------------------------------------------------------------


class TestBodyGroove:
    """Tests for ``fc body groove``."""

    def test_groove(self, mock_backend: MockBackend, runner):
        """Add a groove feature to a body."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["body", "groove", "Body", "Sketch"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_groove_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for groove."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "body", "groove", "Body", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_groove_missing_args(self, runner):
        """Groove without required arguments should fail."""
        result = runner.invoke(cli, ["body", "groove", "Body"])
        assert result.exit_code != 0


# ── body list ----------------------------------------------------------------


class TestBodyList:
    """Tests for ``fc body list``."""

    def test_list(self, mock_backend: MockBackend, runner):
        """List all bodies."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["body", "list"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_list_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for list."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "body", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# ── body get -----------------------------------------------------------------


class TestBodyGet:
    """Tests for ``fc body get``."""

    def test_get(self, mock_backend: MockBackend, runner):
        """Get body details."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["body", "get", "Body"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_get_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for get."""
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "body", "get", "Body"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_get_missing_name(self, runner):
        """Get without a name argument should fail."""
        result = runner.invoke(cli, ["body", "get"])
        assert result.exit_code != 0


# ── error handling -----------------------------------------------------------


class TestBodyErrors:
    """Tests for error handling in body commands."""

    def test_new_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on new, command should output error JSON."""
        mock_backend.stage_response(
            "body_new",
            ToolResponse.error("body_new", "CREATE_FAILED", "Simulated failure"),
        )
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "body", "new", "-n", "FailBody"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"

    def test_pad_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on pad, command should output error JSON."""
        mock_backend.stage_response(
            "body_pad",
            ToolResponse.error("body_pad", "PAD_FAILED", "Simulated failure"),
        )
        with _patch_body_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "body", "pad", "Body", "Sketch"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"
