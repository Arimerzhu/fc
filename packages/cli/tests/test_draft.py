"""Tests for the ``draft`` command group.

Covers draft sub-commands: line, wire, circle, arc, rect, polygon, text,
dimension, array, offset, move, rotate, scale, trim, list, clone, mirror,
stretch, upgrade, downgrade, path-array, point-array, point, facebinder, label.
Uses MockBackend so no real FreeCAD installation is required.
"""

from __future__ import annotations

import json

from fc_cli.main import cli
from fc_core.types import ToolResponse

from tests.conftest import MockBackend

# -- helpers ------------------------------------------------------------------


def _json_output(result) -> dict:
    """Parse JSON from Click result output."""
    return json.loads(result.output.strip())


def _patch_draft_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.draft."""
    from unittest.mock import patch
    return patch("fc_cli.commands.draft._get_backend", return_value=mock)


# -- draft line ---------------------------------------------------------------


class TestDraftLine:
    """Tests for ``fc draft line``."""

    def test_line_default(self, mock_backend: MockBackend, runner):
        """Create a line with default parameters."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "line"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_line_custom_points(self, mock_backend: MockBackend, runner):
        """Create a line with custom start and end points."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "line", "-s", "1,2,3", "-e", "4,5,6",
            ])
        assert result.exit_code == 0

    def test_line_with_name(self, mock_backend: MockBackend, runner):
        """Create a line with a custom name."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "line", "-n", "MyLine"])
        assert result.exit_code == 0

    def test_line_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft line."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "line"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"

    def test_line_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called."""
        with _patch_draft_backend(mock_backend):
            runner.invoke(cli, ["draft", "line"])
        assert mock_backend.disconnected is True


# -- draft wire ---------------------------------------------------------------


class TestDraftWire:
    """Tests for ``fc draft wire``."""

    def test_wire_basic(self, mock_backend: MockBackend, runner):
        """Create a wire with required points."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "wire", "-p", "0,0,0;1,0,0;1,1,0",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_wire_closed(self, mock_backend: MockBackend, runner):
        """Create a closed wire."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "wire", "-p", "0,0,0;1,0,0;1,1,0", "--closed",
            ])
        assert result.exit_code == 0

    def test_wire_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft wire."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "draft", "wire", "-p", "0,0,0;1,0,0",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_wire_missing_points(self, runner):
        """Wire without --points should fail."""
        result = runner.invoke(cli, ["draft", "wire"])
        assert result.exit_code != 0


# -- draft circle -------------------------------------------------------------


class TestDraftCircle:
    """Tests for ``fc draft circle``."""

    def test_circle_default(self, mock_backend: MockBackend, runner):
        """Create a circle with default parameters."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "circle"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_circle_custom_radius(self, mock_backend: MockBackend, runner):
        """Create a circle with custom radius."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "circle", "-r", "10.0"])
        assert result.exit_code == 0

    def test_circle_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft circle."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "circle"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- draft arc ----------------------------------------------------------------


class TestDraftArc:
    """Tests for ``fc draft arc``."""

    def test_arc_default(self, mock_backend: MockBackend, runner):
        """Create an arc with default parameters."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "arc"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_arc_custom_angles(self, mock_backend: MockBackend, runner):
        """Create an arc with custom angles."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "arc", "--start-angle", "0", "--end-angle", "180",
            ])
        assert result.exit_code == 0

    def test_arc_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft arc."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "arc"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- draft rect ---------------------------------------------------------------


class TestDraftRect:
    """Tests for ``fc draft rect``."""

    def test_rect_default(self, mock_backend: MockBackend, runner):
        """Create a rectangle with default parameters."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "rect"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_rect_custom_size(self, mock_backend: MockBackend, runner):
        """Create a rectangle with custom width and height."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "rect", "-w", "20", "-h", "15"])
        assert result.exit_code == 0

    def test_rect_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft rect."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "rect"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- draft polygon ------------------------------------------------------------


class TestDraftPolygon:
    """Tests for ``fc draft polygon``."""

    def test_polygon_default(self, mock_backend: MockBackend, runner):
        """Create a polygon with default parameters."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "polygon"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_polygon_custom_sides(self, mock_backend: MockBackend, runner):
        """Create a polygon with custom sides."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "polygon", "-s", "8"])
        assert result.exit_code == 0

    def test_polygon_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft polygon."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "polygon"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- draft text ---------------------------------------------------------------


class TestDraftText:
    """Tests for ``fc draft text``."""

    def test_text_basic(self, mock_backend: MockBackend, runner):
        """Create text with required text argument."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "text", "Hello World"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_text_with_position(self, mock_backend: MockBackend, runner):
        """Create text at a specific position."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "text", "Hello", "-pos", "10,20,0",
            ])
        assert result.exit_code == 0

    def test_text_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft text."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "text", "Test"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_text_missing_argument(self, runner):
        """Text without text argument should fail."""
        result = runner.invoke(cli, ["draft", "text"])
        assert result.exit_code != 0


# -- draft dimension ----------------------------------------------------------


class TestDraftDimension:
    """Tests for ``fc draft dimension``."""

    def test_dimension_basic(self, mock_backend: MockBackend, runner):
        """Create a dimension with required points."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "dimension", "-s", "0,0,0", "-e", "10,0,0",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_dimension_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft dimension."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "draft", "dimension", "-s", "0,0,0", "-e", "10,0,0",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_dimension_missing_args(self, runner):
        """Dimension without required args should fail."""
        result = runner.invoke(cli, ["draft", "dimension"])
        assert result.exit_code != 0


# -- draft array --------------------------------------------------------------


class TestDraftArray:
    """Tests for ``fc draft array``."""

    def test_array_polar(self, mock_backend: MockBackend, runner):
        """Create a polar array."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "array", "MyObj", "--type", "polar", "-c", "6",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_array_rectangular(self, mock_backend: MockBackend, runner):
        """Create a rectangular array."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "array", "MyObj", "--type", "rectangular",
                "--rows", "3", "--cols", "4",
            ])
        assert result.exit_code == 0

    def test_array_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft array."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "draft", "array", "MyObj", "--type", "polar",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- draft offset -------------------------------------------------------------


class TestDraftOffset:
    """Tests for ``fc draft offset``."""

    def test_offset_basic(self, mock_backend: MockBackend, runner):
        """Create an offset of an object."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "offset", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_offset_with_distance(self, mock_backend: MockBackend, runner):
        """Create an offset with custom distance."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "offset", "MyObj", "-d", "5.0"])
        assert result.exit_code == 0

    def test_offset_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft offset."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "offset", "MyObj"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- draft move ---------------------------------------------------------------


class TestDraftMove:
    """Tests for ``fc draft move``."""

    def test_move_basic(self, mock_backend: MockBackend, runner):
        """Move an object."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "move", "MyObj", "-v", "10,20,30",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_move_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft move."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "draft", "move", "MyObj", "-v", "1,2,3",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_move_missing_vector(self, runner):
        """Move without --vector should fail."""
        result = runner.invoke(cli, ["draft", "move", "MyObj"])
        assert result.exit_code != 0


# -- draft rotate -------------------------------------------------------------


class TestDraftRotate:
    """Tests for ``fc draft rotate``."""

    def test_rotate_basic(self, mock_backend: MockBackend, runner):
        """Rotate an object."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "rotate", "MyObj", "-a", "45",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_rotate_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft rotate."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "draft", "rotate", "MyObj", "-a", "90",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_rotate_missing_angle(self, runner):
        """Rotate without --angle should fail."""
        result = runner.invoke(cli, ["draft", "rotate", "MyObj"])
        assert result.exit_code != 0


# -- draft scale --------------------------------------------------------------


class TestDraftScale:
    """Tests for ``fc draft scale``."""

    def test_scale_basic(self, mock_backend: MockBackend, runner):
        """Scale an object."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "scale", "MyObj", "-f", "2.0",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_scale_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft scale."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "draft", "scale", "MyObj", "-f", "1.5",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_scale_missing_factor(self, runner):
        """Scale without --factor should fail."""
        result = runner.invoke(cli, ["draft", "scale", "MyObj"])
        assert result.exit_code != 0


# -- draft trim ---------------------------------------------------------------


class TestDraftTrim:
    """Tests for ``fc draft trim``."""

    def test_trim_basic(self, mock_backend: MockBackend, runner):
        """Trim geometry."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "trim", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_trim_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft trim."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "trim", "MyObj"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- draft list ---------------------------------------------------------------


class TestDraftList:
    """Tests for ``fc draft list``."""

    def test_list_basic(self, mock_backend: MockBackend, runner):
        """List all Draft objects."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "list"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_list_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft list."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"
        assert data["operation"] == "execute_code"


# -- draft clone --------------------------------------------------------------


class TestDraftClone:
    """Tests for ``fc draft clone``."""

    def test_clone_basic(self, mock_backend: MockBackend, runner):
        """Clone a Draft object."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "clone", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_clone_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft clone."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "clone", "MyObj"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- draft mirror -------------------------------------------------------------


class TestDraftMirror:
    """Tests for ``fc draft mirror``."""

    def test_mirror_basic(self, mock_backend: MockBackend, runner):
        """Mirror a Draft object."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "mirror", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_mirror_axis(self, mock_backend: MockBackend, runner):
        """Mirror with explicit axis."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "mirror", "MyObj", "--axis", "Y"])
        assert result.exit_code == 0

    def test_mirror_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft mirror."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "mirror", "MyObj"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- draft upgrade / downgrade ------------------------------------------------


class TestDraftUpgradeDowngrade:
    """Tests for ``fc draft upgrade`` and ``fc draft downgrade``."""

    def test_upgrade_basic(self, mock_backend: MockBackend, runner):
        """Upgrade a Draft object."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "upgrade", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_upgrade_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft upgrade."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "upgrade", "MyObj"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_downgrade_basic(self, mock_backend: MockBackend, runner):
        """Downgrade a Draft object."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "downgrade", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_downgrade_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft downgrade."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "downgrade", "MyObj"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- draft path-array / point-array -------------------------------------------


class TestDraftArrays:
    """Tests for ``fc draft path-array`` and ``fc draft point-array``."""

    def test_path_array_basic(self, mock_backend: MockBackend, runner):
        """Create a path array."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "path-array", "MyObj", "MyPath",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_path_array_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for path-array."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "draft", "path-array", "MyObj", "MyPath",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_point_array_basic(self, mock_backend: MockBackend, runner):
        """Create a point array."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "point-array", "MyObj", "MyPoints",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_point_array_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for point-array."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "draft", "point-array", "MyObj", "MyPoints",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# -- draft point / facebinder / label -----------------------------------------


class TestDraftMisc:
    """Tests for draft point, facebinder, and label commands."""

    def test_point_basic(self, mock_backend: MockBackend, runner):
        """Create a point."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "point"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_point_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft point."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "point"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_facebinder_basic(self, mock_backend: MockBackend, runner):
        """Create a facebinder."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["draft", "facebinder", "MyObj"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_facebinder_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft facebinder."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "facebinder", "MyObj"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_label_basic(self, mock_backend: MockBackend, runner):
        """Create a label."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "draft", "label", "MyObj", "-t", "This is a label",
            ])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_label_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for draft label."""
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "draft", "label", "MyObj", "-t", "Label",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_label_missing_text(self, runner):
        """Label without --text should fail."""
        result = runner.invoke(cli, ["draft", "label", "MyObj"])
        assert result.exit_code != 0


# -- error handling -----------------------------------------------------------


class TestDraftErrors:
    """Tests for error handling in draft commands."""

    def test_line_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on line, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "CREATE_FAILED", "Simulated failure"),
        )
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "line"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"

    def test_circle_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on circle, command outputs error JSON."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "CREATE_FAILED", "Simulated failure"),
        )
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "draft", "circle"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "error"


# -- draft svg ----------------------------------------------------------------


class TestDraftSvg:
    """Tests for ``fc draft svg``."""

    @staticmethod
    def _box_shape_dict() -> dict:
        """Return a simple box shape as a dict."""
        return {
            "vertices": [
                {"x": 0, "y": 0, "z": 0},
                {"x": 100, "y": 0, "z": 0},
                {"x": 100, "y": 50, "z": 0},
                {"x": 0, "y": 50, "z": 0},
                {"x": 0, "y": 0, "z": 30},
                {"x": 100, "y": 0, "z": 30},
                {"x": 100, "y": 50, "z": 30},
                {"x": 0, "y": 50, "z": 30},
            ],
            "edges": [
                {"p1": {"x": 0, "y": 0, "z": 0}, "p2": {"x": 100, "y": 0, "z": 0}},
                {"p1": {"x": 100, "y": 0, "z": 0}, "p2": {"x": 100, "y": 50, "z": 0}},
                {"p1": {"x": 100, "y": 50, "z": 0}, "p2": {"x": 0, "y": 50, "z": 0}},
                {"p1": {"x": 0, "y": 50, "z": 0}, "p2": {"x": 0, "y": 0, "z": 0}},
                {"p1": {"x": 0, "y": 0, "z": 30}, "p2": {"x": 100, "y": 0, "z": 30}},
                {"p1": {"x": 100, "y": 0, "z": 30}, "p2": {"x": 100, "y": 50, "z": 30}},
                {"p1": {"x": 100, "y": 50, "z": 30}, "p2": {"x": 0, "y": 50, "z": 30}},
                {"p1": {"x": 0, "y": 50, "z": 30}, "p2": {"x": 0, "y": 0, "z": 30}},
                {"p1": {"x": 0, "y": 0, "z": 0}, "p2": {"x": 0, "y": 0, "z": 30}},
                {"p1": {"x": 100, "y": 0, "z": 0}, "p2": {"x": 100, "y": 0, "z": 30}},
                {"p1": {"x": 100, "y": 50, "z": 0}, "p2": {"x": 100, "y": 50, "z": 30}},
                {"p1": {"x": 0, "y": 50, "z": 0}, "p2": {"x": 0, "y": 50, "z": 30}},
            ],
            "bound_box": {
                "x_min": 0, "y_min": 0, "z_min": 0,
                "x_max": 100, "y_max": 50, "z_max": 30,
            },
        }

    def test_svg_from_json(self, runner, tmp_path):
        """Generate SVG from a JSON shape file."""
        input_path = tmp_path / "shape.json"
        output_path = tmp_path / "drawing.svg"
        input_path.write_text(json.dumps(self._box_shape_dict()), encoding="utf-8")

        result = runner.invoke(cli, [
            "--json", "draft", "svg",
            "--input", str(input_path),
            "--output", str(output_path),
            "--page", "A4",
            "--scale", "0.5",
            "--title", "TestBox",
            "--unit", "AI Lab",
            "--material", "Steel",
        ])
        assert result.exit_code == 0, result.output
        assert output_path.exists()
        svg_content = output_path.read_text(encoding="utf-8")
        assert "<svg" in svg_content
        assert "TestBox" in svg_content

    def test_svg_from_fcstd_uses_backend(self, mock_backend: MockBackend, runner, tmp_path):
        """FCStd input requires backend to extract shape data."""
        input_path = tmp_path / "model.FCStd"
        output_path = tmp_path / "drawing.svg"
        input_path.write_text("fake", encoding="utf-8")

        mock_backend.stage_response(
            "execute_code",
            ToolResponse.ok("execute_code", {
                "status": "ok",
                "data": {"shape": self._box_shape_dict()},
                "message": "",
            }),
        )
        with _patch_draft_backend(mock_backend):
            result = runner.invoke(cli, [
                "--json", "draft", "svg",
                "--input", str(input_path),
                "--output", str(output_path),
            ])
        assert result.exit_code == 0, result.output
        assert mock_backend.connected is True
        assert mock_backend.disconnected is True
        assert mock_backend.was_called("execute_code")
        assert output_path.exists()

    def test_svg_help(self, runner):
        """The svg subcommand should provide help."""
        result = runner.invoke(cli, ["draft", "svg", "--help"])
        assert result.exit_code == 0
        assert "--input" in result.output
        assert "--output" in result.output
