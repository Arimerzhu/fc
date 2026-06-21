"""Tests for the ``import`` command group.

Covers all import sub-commands: auto, step, stl, obj, dxf, brep, info.
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


def _patch_import_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.import_cmd."""
    from unittest.mock import patch
    return patch("fc_cli.commands.import_cmd._get_backend", return_value=mock)


def _tmp_file(suffix: str = ".step") -> str:
    """Create a real temp file (import commands check file existence)."""
    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    path = f.name
    f.close()  # keep the file
    return path


# ── import step --------------------------------------------------------------


class TestImportStep:
    """Tests for ``fc import step``."""

    def test_import_step(self, mock_backend: MockBackend, runner):
        """Import a STEP file."""
        tmp = _tmp_file(".step")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["import", "step", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp)

    def test_import_step_json(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for step import."""
        tmp = _tmp_file(".step")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "import", "step", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
            assert data["operation"] == "execute_code"
        finally:
            os.unlink(tmp)

    def test_import_step_missing_file(self, runner):
        """Import a non-existent file should fail."""
        result = runner.invoke(cli, ["import", "step", "no_such_file.step"])
        assert result.exit_code != 0

    def test_import_step_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called."""
        tmp = _tmp_file(".step")
        try:
            with _patch_import_backend(mock_backend):
                runner.invoke(cli, ["import", "step", tmp])
            assert mock_backend.disconnected is True
        finally:
            os.unlink(tmp)


# ── import stl ---------------------------------------------------------------


class TestImportStl:
    """Tests for ``fc import stl``."""

    def test_import_stl(self, mock_backend: MockBackend, runner):
        """Import an STL file."""
        tmp = _tmp_file(".stl")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["import", "stl", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp)

    def test_import_stl_json(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for STL import."""
        tmp = _tmp_file(".stl")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "import", "stl", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            os.unlink(tmp)


# ── import obj ---------------------------------------------------------------


class TestImportObj:
    """Tests for ``fc import obj``."""

    def test_import_obj(self, mock_backend: MockBackend, runner):
        """Import an OBJ file."""
        tmp = _tmp_file(".obj")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["import", "obj", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp)

    def test_import_obj_json(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for OBJ import."""
        tmp = _tmp_file(".obj")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "import", "obj", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            os.unlink(tmp)


# ── import dxf ---------------------------------------------------------------


class TestImportDxf:
    """Tests for ``fc import dxf``."""

    def test_import_dxf(self, mock_backend: MockBackend, runner):
        """Import a DXF file."""
        tmp = _tmp_file(".dxf")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["import", "dxf", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp)

    def test_import_dxf_json(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for DXF import."""
        tmp = _tmp_file(".dxf")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "import", "dxf", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            os.unlink(tmp)


# ── import brep --------------------------------------------------------------


class TestImportBrep:
    """Tests for ``fc import brep``."""

    def test_import_brep(self, mock_backend: MockBackend, runner):
        """Import a BREP file."""
        tmp = _tmp_file(".brep")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["import", "brep", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp)

    def test_import_brep_json(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for BREP import."""
        tmp = _tmp_file(".brep")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "import", "brep", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            os.unlink(tmp)


# ── import auto --------------------------------------------------------------


class TestImportAuto:
    """Tests for ``fc import auto``."""

    def test_auto_detect_step(self, mock_backend: MockBackend, runner):
        """Auto-detect STEP format from extension."""
        tmp = _tmp_file(".step")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["import", "auto", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp)

    def test_auto_detect_stl(self, mock_backend: MockBackend, runner):
        """Auto-detect STL format from extension."""
        tmp = _tmp_file(".stl")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["import", "auto", tmp])
            assert result.exit_code == 0
        finally:
            os.unlink(tmp)

    def test_auto_json(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for auto import."""
        tmp = _tmp_file(".step")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "import", "auto", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            os.unlink(tmp)

    def test_auto_missing_file(self, runner):
        """Auto import of non-existent file should fail."""
        result = runner.invoke(cli, ["import", "auto", "no_such_file.step"])
        assert result.exit_code != 0


# ── import info --------------------------------------------------------------


class TestImportInfo:
    """Tests for ``fc import info``."""

    def test_info_step(self, mock_backend: MockBackend, runner):
        """Get info about a STEP file (non-mesh format, no backend call)."""
        tmp = _tmp_file(".step")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["import", "info", tmp])
            assert result.exit_code == 0
            # For non-mesh formats, no backend call is made
        finally:
            os.unlink(tmp)

    def test_info_stl(self, mock_backend: MockBackend, runner):
        """Get info about an STL file (mesh format, backend called)."""
        tmp = _tmp_file(".stl")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["import", "info", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp)

    def test_info_json(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for info."""
        tmp = _tmp_file(".step")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "import", "info", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            # info outputs a plain dict with file metadata
            assert "file" in data
            assert "format" in data
        finally:
            os.unlink(tmp)

    def test_info_missing_file(self, runner):
        """Info for non-existent file should fail."""
        result = runner.invoke(cli, ["import", "info", "no_such_file.step"])
        assert result.exit_code != 0


# ── error handling -----------------------------------------------------------


class TestImportErrors:
    """Tests for error handling in import commands."""

    def test_step_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on import, command should output error."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "IMPORT_FAILED", "Simulated failure"),
        )
        tmp = _tmp_file(".step")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "import", "step", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "error"
        finally:
            os.unlink(tmp)

    def test_stl_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on STL import, command should output error."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "IMPORT_FAILED", "Simulated STL failure"),
        )
        tmp = _tmp_file(".stl")
        try:
            with _patch_import_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "import", "stl", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "error"
        finally:
            os.unlink(tmp)
