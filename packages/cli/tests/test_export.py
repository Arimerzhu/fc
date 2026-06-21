"""Tests for the ``export`` command group.

Covers all export sub-commands: step, stl, obj, brep, dxf, svg, pdf, gltf,
3mf, fcstd, presets.
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


def _patch_export_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.export."""
    from unittest.mock import patch
    return patch("fc_cli.commands.export._get_backend", return_value=mock)


def _tmp_file(suffix: str = ".step") -> str:
    """Create a temp file path and remove the file so mock can create it."""
    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    path = f.name
    f.close()
    os.unlink(path)
    return path


# ── export step --------------------------------------------------------------


class TestExportStep:
    """Tests for ``fc export step``."""

    def test_step(self, mock_backend: MockBackend, runner):
        """Export to STEP format."""
        tmp = _tmp_file(".step")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["export", "step", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("export")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_step_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for step export."""
        tmp = _tmp_file(".step")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "step", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
            assert data["operation"] == "export"
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_step_missing_output(self, runner):
        """Export step without output argument should fail."""
        result = runner.invoke(cli, ["export", "step"])
        assert result.exit_code != 0


# ── export stl --------------------------------------------------------------


class TestExportStl:
    """Tests for ``fc export stl``."""

    def test_stl(self, mock_backend: MockBackend, runner):
        """Export to STL format."""
        tmp = _tmp_file(".stl")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["export", "stl", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("export")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_stl_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for STL export."""
        tmp = _tmp_file(".stl")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "stl", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# ── export obj --------------------------------------------------------------


class TestExportObj:
    """Tests for ``fc export obj``."""

    def test_obj(self, mock_backend: MockBackend, runner):
        """Export to OBJ format."""
        tmp = _tmp_file(".obj")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["export", "obj", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("export")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_obj_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for OBJ export."""
        tmp = _tmp_file(".obj")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "obj", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# ── export brep -------------------------------------------------------------


class TestExportBrep:
    """Tests for ``fc export brep``."""

    def test_brep(self, mock_backend: MockBackend, runner):
        """Export to BREP format."""
        tmp = _tmp_file(".brep")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["export", "brep", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("export")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_brep_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for BREP export."""
        tmp = _tmp_file(".brep")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "brep", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# ── export dxf --------------------------------------------------------------


class TestExportDxf:
    """Tests for ``fc export dxf``."""

    def test_dxf(self, mock_backend: MockBackend, runner):
        """Export to DXF format."""
        tmp = _tmp_file(".dxf")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["export", "dxf", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("export")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_dxf_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for DXF export."""
        tmp = _tmp_file(".dxf")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "dxf", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# ── export svg --------------------------------------------------------------


class TestExportSvg:
    """Tests for ``fc export svg``."""

    def test_svg(self, mock_backend: MockBackend, runner):
        """Export to SVG format."""
        tmp = _tmp_file(".svg")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["export", "svg", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("export")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_svg_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for SVG export."""
        tmp = _tmp_file(".svg")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "svg", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# ── export pdf --------------------------------------------------------------


class TestExportPdf:
    """Tests for ``fc export pdf``."""

    def test_pdf(self, mock_backend: MockBackend, runner):
        """Export to PDF format (mock doesn't create real file, so os.path.isfile check fails)."""
        tmp = _tmp_file(".pdf")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["export", "pdf", tmp])
            # PDF export checks os.path.isfile(); mock doesn't create real file,
            # so the command outputs an error and exits with code 1.
            assert result.exit_code != 0
            assert mock_backend.was_called("execute_code")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_pdf_json_output(self, mock_backend: MockBackend, runner):
        """PDF export with --json: mock doesn't create real file, so error."""
        tmp = _tmp_file(".pdf")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "pdf", tmp])
            # Same as above: os.path.isfile check fails with mock
            assert result.exit_code != 0
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# ── export gltf -------------------------------------------------------------


class TestExportGltf:
    """Tests for ``fc export gltf``."""

    def test_gltf(self, mock_backend: MockBackend, runner):
        """Export to glTF format."""
        tmp = _tmp_file(".gltf")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["export", "gltf", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("export")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_gltf_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for glTF export."""
        tmp = _tmp_file(".gltf")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "gltf", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# ── export 3mf --------------------------------------------------------------


class TestExport3mf:
    """Tests for ``fc export 3mf``."""

    def test_3mf(self, mock_backend: MockBackend, runner):
        """Export to 3MF format."""
        tmp = _tmp_file(".3mf")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["export", "3mf", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("export")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_3mf_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for 3MF export."""
        tmp = _tmp_file(".3mf")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "3mf", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# ── export fcstd ------------------------------------------------------------


class TestExportFcstd:
    """Tests for ``fc export fcstd``."""

    def test_fcstd(self, mock_backend: MockBackend, runner):
        """Export to FCSTD format."""
        tmp = _tmp_file(".FCStd")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["export", "fcstd", tmp])
            assert result.exit_code == 0
            assert mock_backend.was_called("document_save")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_fcstd_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for FCSTD export."""
        tmp = _tmp_file(".FCStd")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "fcstd", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
            assert data["operation"] == "document_save"
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# ── export presets ----------------------------------------------------------


class TestExportPresets:
    """Tests for ``fc export presets``."""

    def test_presets(self, mock_backend: MockBackend, runner):
        """List export presets."""
        with _patch_export_backend(mock_backend):
            result = runner.invoke(cli, ["export", "presets"])
        assert result.exit_code == 0

    def test_presets_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce output for presets (plain dict, not ToolResponse)."""
        with _patch_export_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "export", "presets"])
        assert result.exit_code == 0
        data = _json_output(result)
        # presets outputs a plain dict of format info, no "status" key
        assert "step" in data


# ── error handling -----------------------------------------------------------


class TestExportErrors:
    """Tests for error handling in export commands."""

    def test_step_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on export, command should output error JSON."""
        mock_backend.stage_response(
            "export",
            ToolResponse.error("export", "EXPORT_FAILED", "Simulated failure"),
        )
        tmp = _tmp_file(".step")
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "step", tmp])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "error"
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_step_file_exists_no_overwrite(self, mock_backend: MockBackend, runner):
        """Export to existing file without --overwrite should fail (error exits with code 1)."""
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
            tmp = f.name
        try:
            with _patch_export_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "export", "step", tmp])
            # _output.error() calls sys.exit(1) when not in repl_mode
            assert result.exit_code != 0
        finally:
            os.unlink(tmp)
