"""Tests for the ``mesh`` command group.

Covers mesh sub-commands: import, export, analyze, repair, refine, decimate,
boolean, section, list, info, create, evaluate, flip-normals, smooth.
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


def _patch_mesh_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.mesh."""
    from unittest.mock import patch
    return patch("fc_cli.commands.mesh._get_backend", return_value=mock)


# -- mesh import --------------------------------------------------------------


class TestMeshImport:
    """Tests for ``fc mesh import``."""

    def test_import_basic(self, mock_backend: MockBackend, runner):
        """Import a mesh file."""
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_mesh_backend(mock_backend):
                result = runner.invoke(cli, ["mesh", "import", tmp_path])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp_path)

    def test_import_with_name(self, mock_backend: MockBackend, runner):
        """Import a mesh file with a custom name."""
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_mesh_backend(mock_backend):
                result = runner.invoke(cli, ["mesh", "import", tmp_path, "-n", "MyMesh"])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp_path)

    def test_import_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh import."""
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_mesh_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "mesh", "import", tmp_path])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "ok"
            assert data["operation"] == "execute_code"
        finally:
            os.unlink(tmp_path)

    def test_import_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called after import."""
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_mesh_backend(mock_backend):
                runner.invoke(cli, ["mesh", "import", tmp_path])
            assert mock_backend.disconnected is True
        finally:
            os.unlink(tmp_path)

    def test_import_nonexistent_file(self, runner):
        """Import a non-existent file should fail."""
        result = runner.invoke(cli, ["mesh", "import", "no_such_file.stl"])
        assert result.exit_code != 0


# -- mesh export --------------------------------------------------------------


class TestMeshExport:
    """Tests for ``fc mesh export``."""

    def test_export_basic(self, mock_backend: MockBackend, runner):
        """Export mesh to file."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "export", "output.stl"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_export_with_format(self, mock_backend: MockBackend, runner):
        """Export mesh with explicit format."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "export", "output.obj", "-f", "obj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_export_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh export."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "export", "output.stl"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_export_overwrite(self, mock_backend: MockBackend, runner):
        """Export with --overwrite flag on existing file."""
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_mesh_backend(mock_backend):
                result = runner.invoke(cli, ["mesh", "export", tmp_path, "--overwrite"])
            assert result.exit_code == 0
            assert mock_backend.was_called("execute_code")
        finally:
            os.unlink(tmp_path)

    def test_export_existing_no_overwrite(self, mock_backend: MockBackend, runner):
        """Export to existing file without --overwrite should fail."""
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_mesh_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "mesh", "export", tmp_path])
            # _output.error() calls sys.exit(1) when not in repl mode
            assert result.exit_code != 0
            data = _json_output(result)
            assert data["status"] == "error"
        finally:
            os.unlink(tmp_path)


# -- mesh analyze -------------------------------------------------------------


class TestMeshAnalyze:
    """Tests for ``fc mesh analyze``."""

    def test_analyze_basic(self, mock_backend: MockBackend, runner):
        """Analyze mesh quality."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "analyze"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_analyze_with_name(self, mock_backend: MockBackend, runner):
        """Analyze a specific mesh by name."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "analyze", "-n", "MyMesh"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_analyze_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh analyze."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "analyze"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- mesh repair --------------------------------------------------------------


class TestMeshRepair:
    """Tests for ``fc mesh repair``."""

    def test_repair_basic(self, mock_backend: MockBackend, runner):
        """Repair mesh with default options."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "repair"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_repair_with_name(self, mock_backend: MockBackend, runner):
        """Repair a specific mesh by name."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "repair", "-n", "MyMesh"])
        assert result.exit_code == 0

    def test_repair_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh repair."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "repair"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_repair_specific_flags(self, mock_backend: MockBackend, runner):
        """Repair with specific fix flags."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, [
                "mesh", "repair", "--fix-degenerates", "--fix-normals",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")


# -- mesh refine --------------------------------------------------------------


class TestMeshRefine:
    """Tests for ``fc mesh refine``."""

    def test_refine_basic(self, mock_backend: MockBackend, runner):
        """Refine mesh with default iterations."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "refine"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_refine_with_iterations(self, mock_backend: MockBackend, runner):
        """Refine mesh with custom iterations."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "refine", "-i", "3"])
        assert result.exit_code == 0

    def test_refine_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh refine."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "refine"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- mesh decimate ------------------------------------------------------------


class TestMeshDecimate:
    """Tests for ``fc mesh decimate``."""

    def test_decimate_basic(self, mock_backend: MockBackend, runner):
        """Decimate mesh with default reduction."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "decimate"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_decimate_with_reduction(self, mock_backend: MockBackend, runner):
        """Decimate mesh with custom reduction factor."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "decimate", "-r", "0.75"])
        assert result.exit_code == 0

    def test_decimate_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh decimate."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "decimate"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- mesh boolean -------------------------------------------------------------


class TestMeshBoolean:
    """Tests for ``fc mesh boolean``."""

    def test_boolean_cut(self, mock_backend: MockBackend, runner):
        """Boolean cut operation."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "boolean", "cut", "MeshA", "MeshB"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_boolean_fuse(self, mock_backend: MockBackend, runner):
        """Boolean fuse operation."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "boolean", "fuse", "MeshA", "MeshB"])
        assert result.exit_code == 0

    def test_boolean_common(self, mock_backend: MockBackend, runner):
        """Boolean common operation."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "boolean", "common", "MeshA", "MeshB"])
        assert result.exit_code == 0

    def test_boolean_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh boolean."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "mesh", "boolean", "cut", "MeshA", "MeshB",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_boolean_with_name(self, mock_backend: MockBackend, runner):
        """Boolean with custom result name."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, [
                "mesh", "boolean", "cut", "MeshA", "MeshB", "-n", "CutResult",
            ])
        assert result.exit_code == 0

    def test_boolean_invalid_operation(self, runner):
        """Invalid boolean operation should fail."""
        result = runner.invoke(cli, ["mesh", "boolean", "invalid", "A", "B"])
        assert result.exit_code != 0

    def test_boolean_missing_args(self, runner):
        """Missing required arguments should fail."""
        result = runner.invoke(cli, ["mesh", "boolean", "cut"])
        assert result.exit_code != 0


# -- mesh section -------------------------------------------------------------


class TestMeshSection:
    """Tests for ``fc mesh section``."""

    def test_section_basic(self, mock_backend: MockBackend, runner):
        """Create a cross-section with default plane."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "section"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_section_with_plane(self, mock_backend: MockBackend, runner):
        """Create a cross-section with explicit plane."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "section", "--plane", "XZ"])
        assert result.exit_code == 0

    def test_section_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh section."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "section"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- mesh list ----------------------------------------------------------------


class TestMeshList:
    """Tests for ``fc mesh list``."""

    def test_list_basic(self, mock_backend: MockBackend, runner):
        """List all mesh objects."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "list"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_list_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh list."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- mesh info ----------------------------------------------------------------


class TestMeshInfo:
    """Tests for ``fc mesh info``."""

    def test_info_basic(self, mock_backend: MockBackend, runner):
        """Get mesh info by name."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "info", "MyMesh"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_info_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh info."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "info", "MyMesh"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_info_missing_name(self, runner):
        """Info without name argument should fail."""
        result = runner.invoke(cli, ["mesh", "info"])
        assert result.exit_code != 0


# -- mesh create --------------------------------------------------------------


class TestMeshCreate:
    """Tests for ``fc mesh create``."""

    def test_create_cube(self, mock_backend: MockBackend, runner):
        """Create a cube mesh primitive."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "create", "cube"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_create_sphere(self, mock_backend: MockBackend, runner):
        """Create a sphere mesh primitive."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "create", "sphere"])
        assert result.exit_code == 0

    def test_create_with_name(self, mock_backend: MockBackend, runner):
        """Create mesh with custom name."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "create", "cube", "-n", "MyCube"])
        assert result.exit_code == 0

    def test_create_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh create."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "create", "cube"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- mesh evaluate ------------------------------------------------------------


class TestMeshEvaluate:
    """Tests for ``fc mesh evaluate``."""

    def test_evaluate_basic(self, mock_backend: MockBackend, runner):
        """Evaluate mesh quality."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "evaluate", "MyMesh"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_evaluate_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh evaluate."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "evaluate", "MyMesh"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- mesh flip-normals --------------------------------------------------------


class TestMeshFlipNormals:
    """Tests for ``fc mesh flip-normals``."""

    def test_flip_normals_basic(self, mock_backend: MockBackend, runner):
        """Flip mesh normals."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "flip-normals", "MyMesh"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_flip_normals_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh flip-normals."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "flip-normals", "MyMesh"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- mesh smooth --------------------------------------------------------------


class TestMeshSmooth:
    """Tests for ``fc mesh smooth``."""

    def test_smooth_basic(self, mock_backend: MockBackend, runner):
        """Smooth a mesh."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["mesh", "smooth", "MyMesh"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_smooth_with_options(self, mock_backend: MockBackend, runner):
        """Smooth with custom iterations and factor."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, [
                "mesh", "smooth", "MyMesh", "--iterations", "5", "--factor", "0.8",
            ])
        assert result.exit_code == 0

    def test_smooth_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mesh smooth."""
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "smooth", "MyMesh"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- error handling -----------------------------------------------------------


class TestMeshErrors:
    """Tests for error handling in mesh commands."""

    def test_import_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on import, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "IMPORT_FAILED", "Simulated failure"),
        )
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp_path = f.name
        try:
            with _patch_mesh_backend(mock_backend):
                result = runner.invoke(cli, ["--json", "mesh", "import", tmp_path])
            assert result.exit_code == 0
            data = _json_output(result)
            assert data["status"] == "error"
        finally:
            os.unlink(tmp_path)

    def test_analyze_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on analyze, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "ANALYZE_FAILED", "Simulated failure"),
        )
        with _patch_mesh_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "mesh", "analyze"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"
