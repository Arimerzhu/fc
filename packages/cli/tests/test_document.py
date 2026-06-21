"""Tests for the ``document`` command group.

Covers all 6 sub-commands: new, open, save, info, close, list.
Uses MockBackend so no real FreeCAD installation is required.
"""

from __future__ import annotations

import json
import os
import tempfile

from fc_core.types import ToolResponse
from fc_cli.main import cli

from tests.conftest import MockBackend, _patch_get_backend


# ── helpers ------------------------------------------------------------------


def _json_output(result) -> dict:
    """Parse JSON from Click result output."""
    return json.loads(result.output.strip())


# ── document new -------------------------------------------------------------

class TestDocumentNew:
    """Tests for ``fc document new``."""

    def test_new_default_name(self, mock_backend: MockBackend, runner):
        """Create a document with the default name."""
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["document", "new"])
        assert result.exit_code == 0
        assert mock_backend.was_called("document_new")
        assert mock_backend.calls[0][1][0] == "Untitled"

    def test_new_custom_name(self, mock_backend: MockBackend, runner):
        """Create a document with a custom name."""
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["document", "new", "--name", "MyPart"])
        assert result.exit_code == 0
        assert mock_backend.calls[0][1][0] == "MyPart"

    def test_new_json_output(self, mock_backend: MockBackend, runner):
        """Verify --json flag produces valid JSON with status ok."""
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "document", "new", "-n", "JsonDoc"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "document_new"
        assert data["data"]["name"] == "JsonDoc"

    def test_new_with_output_saves(self, mock_backend: MockBackend, runner):
        """When --output is given, document_save should also be called."""
        with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
            tmp_path = f.name
        # Remove the temp file so the mock doesn't complain about it existing
        os.unlink(tmp_path)
        try:
            with _patch_get_backend(mock_backend):
                result = runner.invoke(cli, [
                    "document", "new", "-n", "SavedDoc", "-o", tmp_path,
                ])
            assert result.exit_code == 0
            assert mock_backend.was_called("document_new")
            assert mock_backend.was_called("document_save")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_new_disconnect_called(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called even on success."""
        with _patch_get_backend(mock_backend):
            runner.invoke(cli, ["document", "new"])
        assert mock_backend.disconnected is True


# ── document open ------------------------------------------------------------

class TestDocumentOpen:
    """Tests for ``fc document open <path>``."""

    def test_open_existing_file(self, mock_backend: MockBackend, runner):
        """Open a file that exists on disk."""
        with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_get_backend(mock_backend):
                result = runner.invoke(cli, ["document", "open", tmp_path])
            assert result.exit_code == 0
            assert mock_backend.was_called("document_open")
        finally:
            os.unlink(tmp_path)

    def test_open_nonexistent_file(self, runner):
        """Opening a file that does not exist should fail (Click Path check)."""
        result = runner.invoke(cli, ["document", "open", "no_such_file.FCStd"])
        assert result.exit_code != 0

    def test_open_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for open command."""
        with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_get_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "document", "open", tmp_path])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
            assert data["operation"] == "document_open"
        finally:
            os.unlink(tmp_path)


# ── document save ------------------------------------------------------------

class TestDocumentSave:
    """Tests for ``fc document save``."""

    def test_save_no_output(self, mock_backend: MockBackend, runner):
        """Save without --output should call document_save with None."""
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["document", "save"])
        assert result.exit_code == 0
        assert mock_backend.was_called("document_save")

    def test_save_with_output(self, mock_backend: MockBackend, runner):
        """Save with --output should pass the path to document_save."""
        with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
            tmp_path = f.name
        os.unlink(tmp_path)
        try:
            with _patch_get_backend(mock_backend):
                result = runner.invoke(cli, ["document", "save", "-o", tmp_path])
            assert result.exit_code == 0
            # Verify the path was passed
            save_call = [c for c in mock_backend.calls if c[0] == "document_save"]
            assert len(save_call) == 1
            assert save_call[0][1][0] == tmp_path
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_save_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for save command."""
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "document", "save"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "document_save"


# ── document info ------------------------------------------------------------

class TestDocumentInfo:
    """Tests for ``fc document info``."""

    def test_info_returns_data(self, mock_backend: MockBackend, runner):
        """Info command should call document_info and return data."""
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["document", "info"])
        assert result.exit_code == 0
        assert mock_backend.was_called("document_info")

    def test_info_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for info command."""
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "document", "info"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "document_info"
        assert "name" in data["data"]


# ── document close -----------------------------------------------------------

class TestDocumentClose:
    """Tests for ``fc document close``."""

    def test_close_calls_backend(self, mock_backend: MockBackend, runner):
        """Close command should call document_close on the backend."""
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["document", "close"])
        assert result.exit_code == 0
        assert mock_backend.was_called("document_close")

    def test_close_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for close command."""
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "document", "close"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "document_close"

    def test_close_disconnect_called(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called after close."""
        with _patch_get_backend(mock_backend):
            runner.invoke(cli, ["document", "close"])
        assert mock_backend.disconnected is True


# ── document list ------------------------------------------------------------

class TestDocumentList:
    """Tests for ``fc document list``."""

    def test_list_calls_object_list(self, mock_backend: MockBackend, runner):
        """List command should call object_list on the backend."""
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["document", "list"])
        assert result.exit_code == 0
        assert mock_backend.was_called("object_list")

    def test_list_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for list command."""
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "document", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "object_list"


# ── error handling -----------------------------------------------------------

class TestDocumentErrors:
    """Tests for error handling in document commands."""

    def test_new_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error response, command should output error JSON."""
        mock_backend.stage_response(
            "document_new",
            ToolResponse.error("document_new", "CREATE_FAILED", "Simulated failure"),
        )
        with _patch_get_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "document", "new", "-n", "FailDoc"])
        # With --json, error response is output as JSON to stdout
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"

    def test_open_backend_error(self, mock_backend: MockBackend, runner):
        """When backend raises on open, command should handle gracefully."""
        mock_backend.stage_response(
            "document_open",
            ToolResponse.error("document_open", "OPEN_FAILED", "Simulated open failure"),
        )
        with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_get_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "document", "open", tmp_path])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "error"
        finally:
            os.unlink(tmp_path)
