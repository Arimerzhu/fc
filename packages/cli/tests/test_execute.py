"""Tests for the ``execute`` command group.

Covers all execute sub-commands: code, file.
Uses MockBackend so no real FreeCAD installation is required.
"""

from __future__ import annotations

import json
import os
import tempfile

from fc_core.types import ToolResponse
from fc_cli.main import cli

from tests.conftest import MockBackend


# ── helpers ------------------------------------------------------------------


def _json_output(result) -> dict:
    """Parse JSON from Click result output."""
    return json.loads(result.output.strip())


def _patch_execute_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.execute."""
    from unittest.mock import patch
    return patch("fc_cli.commands.execute._get_backend", return_value=mock)


# ── execute code -------------------------------------------------------------


class TestExecuteCode:
    """Tests for ``fc execute code``."""

    def test_code_basic(self, mock_backend: MockBackend, runner):
        """Execute a simple code string."""
        with _patch_execute_backend(mock_backend):
            result = runner.invoke(cli, [
                "execute", "code", "print('hello')",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_code_passes_to_backend(self, mock_backend: MockBackend, runner):
        """Code string is passed to backend.execute_code."""
        with _patch_execute_backend(mock_backend):
            result = runner.invoke(cli, [
                "execute", "code", "FreeCAD.ActiveDocument.Name",
            ])
        assert result.exit_code == 0
        call = mock_backend.calls[0]
        assert call[0] == "execute_code"
        assert "FreeCAD.ActiveDocument.Name" in call[1][0]

    def test_code_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for code execution."""
        with _patch_execute_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "execute", "code", "x = 1",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_code_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called after code execution."""
        with _patch_execute_backend(mock_backend):
            runner.invoke(cli, ["execute", "code", "pass"])
        assert mock_backend.disconnected is True

    def test_code_missing_argument(self, runner):
        """Execute code without code argument should fail."""
        result = runner.invoke(cli, ["execute", "code"])
        assert result.exit_code != 0


# ── execute file -------------------------------------------------------------


class TestExecuteFile:
    """Tests for ``fc execute file``."""

    def test_file_basic(self, mock_backend: MockBackend, runner):
        """Execute a macro file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("print('hello from macro')\n")
            tmp = f.name
        try:
            with _patch_execute_backend(mock_backend):
                result = runner.invoke(cli, ["execute", "file", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp)

    def test_file_reads_content(self, mock_backend: MockBackend, runner):
        """File content is read and passed to backend.execute_code."""
        macro_content = "import FreeCAD\nprint(FreeCAD.ActiveDocument.Name)\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(macro_content)
            tmp = f.name
        try:
            with _patch_execute_backend(mock_backend):
                result = runner.invoke(cli, ["execute", "file", tmp])
            assert result.exit_code == 0
            call = mock_backend.calls[0]
            assert call[0] == "execute_code"
            assert "FreeCAD.ActiveDocument.Name" in call[1][0]
        finally:
            os.unlink(tmp)

    def test_file_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for file execution."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("x = 42\n")
            tmp = f.name
        try:
            with _patch_execute_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "execute", "file", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
            assert data["operation"] == "execute_code"
        finally:
            os.unlink(tmp)

    def test_file_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called after file execution."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("pass\n")
            tmp = f.name
        try:
            with _patch_execute_backend(mock_backend):
                runner.invoke(cli, ["execute", "file", tmp])
            assert mock_backend.disconnected is True
        finally:
            os.unlink(tmp)

    def test_file_missing_file(self, runner):
        """Execute a non-existent file should fail."""
        result = runner.invoke(cli, ["execute", "file", "no_such_macro.py"])
        assert result.exit_code != 0

    def test_file_missing_argument(self, runner):
        """Execute file without path argument should fail."""
        result = runner.invoke(cli, ["execute", "file"])
        assert result.exit_code != 0


# ── error handling -----------------------------------------------------------


class TestExecuteErrors:
    """Tests for error handling in execute commands."""

    def test_code_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on code execution, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "EXEC_FAILED", "Simulated failure"),
        )
        with _patch_execute_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "execute", "code", "raise Exception('boom')",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"

    def test_file_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on file execution, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "EXEC_FAILED", "Simulated file failure"),
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("raise RuntimeError('boom')\n")
            tmp = f.name
        try:
            with _patch_execute_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "execute", "file", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "error"
        finally:
            os.unlink(tmp)
