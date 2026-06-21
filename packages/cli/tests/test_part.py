"""Tests for the ``part`` command group.

Covers all part sub-commands: add, remove, list, get, transform, boolean,
copy, mirror, scale, fillet-3d, chamfer-3d, info, bounds, hole.
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


def _patch_part_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.part."""
    from unittest.mock import patch
    return patch("fc_cli.commands.part._get_backend", return_value=mock)


# ── part add ------------------------------------------------------------------


class TestPartAdd:
    """Tests for ``fc part add``."""

    def test_add_box_default(self, mock_backend: MockBackend, runner):
        """Add a box with default parameters."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "add", "box"])
        assert result.exit_code == 0
        assert mock_backend.was_called("object_create")

    def test_add_cylinder(self, mock_backend: MockBackend, runner):
        """Add a cylinder primitive."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "add", "cylinder"])
        assert result.exit_code == 0
        assert mock_backend.was_called("object_create")

    def test_add_sphere(self, mock_backend: MockBackend, runner):
        """Add a sphere primitive."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "add", "sphere"])
        assert result.exit_code == 0
        assert mock_backend.was_called("object_create")

    def test_add_cone(self, mock_backend: MockBackend, runner):
        """Add a cone primitive."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "add", "cone"])
        assert result.exit_code == 0

    def test_add_torus(self, mock_backend: MockBackend, runner):
        """Add a torus primitive."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "add", "torus"])
        assert result.exit_code == 0

    def test_add_with_name(self, mock_backend: MockBackend, runner):
        """Add a part with a custom name."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "add", "box", "-n", "MyBox"])
        assert result.exit_code == 0
        call = [c for c in mock_backend.calls if c[0] == "object_create"][0]
        assert call[1][1] == "MyBox"  # second arg is name

    def test_add_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for part add."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "add", "box", "-n", "JsonBox"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "object_create"

    def test_add_invalid_type(self, mock_backend: MockBackend, runner):
        """Unknown part type should produce an error (non-zero exit)."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "add", "invalid_type"])
        # _output.error() calls sys.exit(1) when not in repl_mode
        assert result.exit_code != 0
        # Error output is JSON on stderr
        data = json.loads(result.output.strip())
        assert data["status"] == "error"

    def test_add_with_params(self, mock_backend: MockBackend, runner):
        """Add a box with custom parameters."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, [
                "part", "add", "box", "-P", "Length=20", "-P", "Width=15", "-P", "Height=10",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("object_create")

    def test_add_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called."""
        with _patch_part_backend(mock_backend):
            runner.invoke(cli, ["part", "add", "box"])
        assert mock_backend.disconnected is True


# ── part remove --------------------------------------------------------------


class TestPartRemove:
    """Tests for ``fc part remove``."""

    def test_remove_part(self, mock_backend: MockBackend, runner):
        """Remove a part by name."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "remove", "Box001"])
        assert result.exit_code == 0
        assert mock_backend.was_called("object_delete")

    def test_remove_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for remove."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "remove", "Box001"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "object_delete"

    def test_remove_missing_name(self, runner):
        """Remove without a name argument should fail."""
        result = runner.invoke(cli, ["part", "remove"])
        assert result.exit_code != 0


# ── part list ----------------------------------------------------------------


class TestPartList:
    """Tests for ``fc part list``."""

    def test_list_parts(self, mock_backend: MockBackend, runner):
        """List all parts."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "list"])
        assert result.exit_code == 0
        assert mock_backend.was_called("object_list")

    def test_list_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for list."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "object_list"


# ── part get -----------------------------------------------------------------


class TestPartGet:
    """Tests for ``fc part get``."""

    def test_get_part(self, mock_backend: MockBackend, runner):
        """Get part details."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "get", "Box001"])
        assert result.exit_code == 0
        assert mock_backend.was_called("object_get")

    def test_get_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for get."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "get", "Box001"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "object_get"

    def test_get_missing_name(self, runner):
        """Get without a name argument should fail."""
        result = runner.invoke(cli, ["part", "get"])
        assert result.exit_code != 0


# ── part transform -----------------------------------------------------------


class TestPartTransform:
    """Tests for ``fc part transform``."""

    def test_transform_position(self, mock_backend: MockBackend, runner):
        """Transform a part's position."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "transform", "Box001", "-pos", "10,20,30"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_transform_rotation(self, mock_backend: MockBackend, runner):
        """Transform a part's rotation."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "transform", "Box001", "-rot", "45,0,0"])
        assert result.exit_code == 0

    def test_transform_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for transform."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "part", "transform", "Box001", "-pos", "10,20,30",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_transform_missing_name(self, runner):
        """Transform without a name argument should fail."""
        result = runner.invoke(cli, ["part", "transform"])
        assert result.exit_code != 0


# ── part boolean -------------------------------------------------------------


class TestPartBoolean:
    """Tests for ``fc part boolean``."""

    def test_boolean_cut(self, mock_backend: MockBackend, runner):
        """Boolean cut operation."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "boolean", "cut", "Box001", "Cylinder001"])
        assert result.exit_code == 0
        assert mock_backend.was_called("boolean_cut")

    def test_boolean_fuse(self, mock_backend: MockBackend, runner):
        """Boolean fuse operation."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "boolean", "fuse", "Box001", "Box002"])
        assert result.exit_code == 0
        assert mock_backend.was_called("boolean_union")

    def test_boolean_common(self, mock_backend: MockBackend, runner):
        """Boolean common operation."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "boolean", "common", "Box001", "Sphere001"])
        assert result.exit_code == 0
        assert mock_backend.was_called("boolean_common")

    def test_boolean_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for boolean."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "part", "boolean", "cut", "Box001", "Cylinder001",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_boolean_invalid_op(self, runner):
        """Invalid boolean operation should fail."""
        result = runner.invoke(cli, ["part", "boolean", "invalid", "A", "B"])
        assert result.exit_code != 0


# ── part copy ----------------------------------------------------------------


class TestPartCopy:
    """Tests for ``fc part copy``."""

    def test_copy_part(self, mock_backend: MockBackend, runner):
        """Copy a part."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "copy", "Box001"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_copy_with_name(self, mock_backend: MockBackend, runner):
        """Copy a part with a custom name."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "copy", "Box001", "-n", "MyCopy"])
        assert result.exit_code == 0

    def test_copy_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for copy."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "copy", "Box001"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# ── part mirror --------------------------------------------------------------


class TestPartMirror:
    """Tests for ``fc part mirror``."""

    def test_mirror_part(self, mock_backend: MockBackend, runner):
        """Mirror a part."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "mirror", "Box001"])
        assert result.exit_code == 0
        assert mock_backend.was_called("mirror_object")

    def test_mirror_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for mirror."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "mirror", "Box001"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "mirror_object"


# ── part scale ---------------------------------------------------------------


class TestPartScale:
    """Tests for ``fc part scale``."""

    def test_scale_uniform(self, mock_backend: MockBackend, runner):
        """Scale a part by a uniform factor."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "scale", "Box001", "2.0"])
        assert result.exit_code == 0
        assert mock_backend.was_called("scale_object")

    def test_scale_xyz(self, mock_backend: MockBackend, runner):
        """Scale a part by x,y,z factors."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "scale", "Box001", "2,3,4"])
        assert result.exit_code == 0

    def test_scale_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for scale."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "scale", "Box001", "1.5"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "scale_object"

    def test_scale_missing_args(self, runner):
        """Scale without factor argument should fail."""
        result = runner.invoke(cli, ["part", "scale", "Box001"])
        assert result.exit_code != 0


# ── part fillet-3d -----------------------------------------------------------


class TestPartFillet3D:
    """Tests for ``fc part fillet-3d``."""

    def test_fillet_default(self, mock_backend: MockBackend, runner):
        """Apply fillet with default radius."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "fillet-3d", "Box001"])
        assert result.exit_code == 0
        assert mock_backend.was_called("fillet_edges")

    def test_fillet_custom_radius(self, mock_backend: MockBackend, runner):
        """Apply fillet with custom radius."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "fillet-3d", "Box001", "-r", "3.0"])
        assert result.exit_code == 0

    def test_fillet_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for fillet-3d."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "fillet-3d", "Box001"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "fillet_edges"


# ── part chamfer-3d ----------------------------------------------------------


class TestPartChamfer3D:
    """Tests for ``fc part chamfer-3d``."""

    def test_chamfer_default(self, mock_backend: MockBackend, runner):
        """Apply chamfer with default size."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "chamfer-3d", "Box001"])
        assert result.exit_code == 0
        assert mock_backend.was_called("chamfer_edges")

    def test_chamfer_custom_size(self, mock_backend: MockBackend, runner):
        """Apply chamfer with custom size."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "chamfer-3d", "Box001", "-s", "2.5"])
        assert result.exit_code == 0

    def test_chamfer_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for chamfer-3d."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "chamfer-3d", "Box001"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "chamfer_edges"


# ── part info ----------------------------------------------------------------


class TestPartInfo:
    """Tests for ``fc part info``."""

    def test_info(self, mock_backend: MockBackend, runner):
        """Get part info."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "info", "Box001"])
        assert result.exit_code == 0
        assert mock_backend.was_called("object_get")

    def test_info_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for info."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "info", "Box001"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "object_get"


# ── part bounds --------------------------------------------------------------


class TestPartBounds:
    """Tests for ``fc part bounds``."""

    def test_bounds(self, mock_backend: MockBackend, runner):
        """Get part bounding box."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "bounds", "Box001"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_bounds_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for bounds."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "bounds", "Box001"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# ── part hole ----------------------------------------------------------------


class TestPartHole:
    """Tests for ``fc part hole``."""

    def test_hole(self, mock_backend: MockBackend, runner):
        """Create a hole in a part."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["part", "hole", "Box001"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_hole_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for hole."""
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "hole", "Box001"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# ── error handling -----------------------------------------------------------


class TestPartErrors:
    """Tests for error handling in part commands."""

    def test_add_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on add, command should output error JSON."""
        mock_backend.stage_response(
            "object_create",
            ToolResponse.error("object_create", "CREATE_FAILED", "Simulated failure"),
        )
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "add", "box", "-n", "FailBox"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"

    def test_remove_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on remove, command should output error JSON."""
        mock_backend.stage_response(
            "object_delete",
            ToolResponse.error("object_delete", "DELETE_FAILED", "Simulated failure"),
        )
        with _patch_part_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "part", "remove", "NonExistent"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"
