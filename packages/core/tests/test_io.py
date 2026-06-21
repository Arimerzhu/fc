"""Tests for fc_core IO module.

Covers:
- export.py: EXPORT_PRESETS, list_presets, get_preset, export_with_preset, export_batch
- import_mod.py: detect_format, get_import_info, list_supported_formats, import_file
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from fc_core.io.export import (
    EXPORT_PRESETS,
    export_batch,
    export_with_preset,
    get_preset,
    list_presets,
)
from fc_core.io.import_mod import (
    ALL_EXTENSIONS,
    CAD_EXTENSIONS,
    DRAFT_EXTENSIONS,
    IMPORT_METHODS,
    MESH_EXTENSIONS,
    detect_format,
    get_import_info,
    import_file,
    list_supported_formats,
)
from fc_core.types import ToolResponse


# ---------------------------------------------------------------------------
# export.py tests
# ---------------------------------------------------------------------------

class TestExportPresets:
    """Tests for export preset definitions and listing."""

    def test_presets_not_empty(self):
        """EXPORT_PRESETS must contain at least one preset."""
        assert len(EXPORT_PRESETS) > 0

    def test_3d_print_preset_exists(self):
        preset = get_preset("3d_print")
        assert preset is not None
        assert preset["format"] == "stl"

    def test_3d_print_fast_preset_exists(self):
        preset = get_preset("3d_print_fast")
        assert preset is not None
        assert preset["format"] == "stl"
        assert preset["tolerance"] == 0.2

    def test_cad_exchange_preset(self):
        preset = get_preset("cad_exchange")
        assert preset is not None
        assert preset["format"] == "step"

    def test_cnc_preset(self):
        preset = get_preset("cnc")
        assert preset is not None
        assert preset["format"] == "step"

    def test_visualization_preset(self):
        preset = get_preset("visualization")
        assert preset is not None
        assert preset["format"] == "obj"

    def test_web_preset(self):
        preset = get_preset("web")
        assert preset is not None
        assert preset["format"] == "gltf"

    def test_mesh_fine_preset(self):
        preset = get_preset("mesh_fine")
        assert preset is not None
        assert preset["tolerance"] == 0.01

    def test_mesh_coarse_preset(self):
        preset = get_preset("mesh_coarse")
        assert preset is not None
        assert preset["tolerance"] == 0.5

    def test_unknown_preset_returns_none(self):
        assert get_preset("nonexistent") is None

    def test_list_presets_returns_dict(self):
        presets = list_presets()
        assert isinstance(presets, dict)
        assert len(presets) == len(EXPORT_PRESETS)

    def test_list_presets_contains_descriptions(self):
        presets = list_presets()
        for name, desc in presets.items():
            assert isinstance(name, str)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_all_presets_have_format(self):
        for name, info in EXPORT_PRESETS.items():
            assert "format" in info, f"Preset '{name}' missing 'format' key"

    def test_all_presets_have_description(self):
        for name, info in EXPORT_PRESETS.items():
            assert "description" in info, f"Preset '{name}' missing 'description' key"


class TestExportWithPreset:
    """Tests for export_with_preset function."""

    @pytest.fixture
    def mock_backend(self):
        backend = MagicMock()
        backend.export.return_value = ToolResponse.ok(
            "export", {"output": "/tmp/test.stl", "format": "stl", "file_size": 1024}
        )
        return backend

    def test_export_with_valid_preset(self, mock_backend, tmp_path):
        out = str(tmp_path / "output.stl")
        r = export_with_preset(mock_backend, out, "3d_print")
        assert r.status == "ok"
        mock_backend.export.assert_called_once()

    def test_export_with_unknown_preset(self, mock_backend, tmp_path):
        out = str(tmp_path / "output.stl")
        r = export_with_preset(mock_backend, out, "nonexistent")
        assert r.status == "error"
        assert r.error_code == "UNKNOWN_PRESET"

    def test_export_file_exists_no_overwrite(self, mock_backend, tmp_path):
        out = str(tmp_path / "existing.stl")
        out_path = tmp_path / "existing.stl"
        out_path.write_text("exists")
        r = export_with_preset(mock_backend, str(out_path), "3d_print", overwrite=False)
        assert r.status == "error"
        assert r.error_code == "FILE_EXISTS"

    def test_export_file_exists_with_overwrite(self, mock_backend, tmp_path):
        out_path = tmp_path / "existing.stl"
        out_path.write_text("exists")
        r = export_with_preset(mock_backend, str(out_path), "3d_print", overwrite=True)
        assert r.status == "ok"

    def test_export_passes_correct_format(self, mock_backend, tmp_path):
        out = str(tmp_path / "output.step")
        export_with_preset(mock_backend, out, "cad_exchange")
        mock_backend.export.assert_called_once_with(out, "step")


class TestExportBatch:
    """Tests for export_batch function."""

    @pytest.fixture
    def mock_backend(self):
        backend = MagicMock()
        backend.export.return_value = ToolResponse.ok(
            "export", {"output": "/tmp/test.stl", "format": "stl", "file_size": 1024}
        )
        return backend

    def test_export_batch_multiple_formats(self, mock_backend, tmp_path):
        results = export_batch(mock_backend, str(tmp_path), "model", ["step", "stl", "obj"])
        assert len(results) == 3
        assert all(r.status == "ok" for r in results)

    def test_export_batch_single_format(self, mock_backend, tmp_path):
        results = export_batch(mock_backend, str(tmp_path), "model", ["step"])
        assert len(results) == 1

    def test_export_batch_empty_formats(self, mock_backend, tmp_path):
        results = export_batch(mock_backend, str(tmp_path), "model", [])
        assert results == []

    def test_export_batch_creates_output_dir(self, mock_backend, tmp_path):
        out_dir = tmp_path / "new_subdir"
        export_batch(mock_backend, str(out_dir), "model", ["step"])
        assert out_dir.exists()

    def test_export_batch_strips_dot_prefix(self, mock_backend, tmp_path):
        export_batch(mock_backend, str(tmp_path), "model", [".step", ".stl"])
        assert mock_backend.export.call_count == 2


# ---------------------------------------------------------------------------
# import_mod.py tests
# ---------------------------------------------------------------------------

class TestDetectFormat:
    """Tests for format auto-detection."""

    def test_detect_stl(self):
        assert detect_format("model.stl") == "mesh"

    def test_detect_obj(self):
        assert detect_format("model.obj") == "mesh"

    def test_detect_ply(self):
        assert detect_format("model.ply") == "mesh"

    def test_detect_step(self):
        assert detect_format("model.step") == "cad"

    def test_detect_stp(self):
        assert detect_format("model.stp") == "cad"

    def test_detect_iges(self):
        assert detect_format("model.iges") == "cad"

    def test_detect_igs(self):
        assert detect_format("model.igs") == "cad"

    def test_detect_brep(self):
        assert detect_format("model.brep") == "cad"

    def test_detect_fcstd(self):
        assert detect_format("model.fcstd") == "freecad"

    def test_detect_dxf(self):
        assert detect_format("model.dxf") == "draft"

    def test_detect_svg(self):
        assert detect_format("model.svg") == "draft"

    def test_detect_3mf(self):
        assert detect_format("model.3mf") == "mesh"

    def test_detect_unknown(self):
        assert detect_format("model.xyz") == "unknown"

    def test_detect_uppercase_extension(self):
        assert detect_format("model.STL") == "mesh"

    def test_detect_mixed_case(self):
        assert detect_format("model.Step") == "cad"


class TestGetImportInfo:
    """Tests for get_import_info function."""

    def test_existing_file(self, tmp_path):
        f = tmp_path / "test.stl"
        f.write_text("solid test")
        info = get_import_info(str(f))
        assert info["exists"] is True
        assert info["extension"] == ".stl"
        assert info["format"] == "mesh"
        assert "file_size" in info

    def test_nonexistent_file(self):
        info = get_import_info("/nonexistent/path/model.step")
        assert info["exists"] is False
        assert info["extension"] == ".step"
        assert info["format"] == "cad"
        assert "file_size" not in info

    def test_info_has_required_keys(self, tmp_path):
        f = tmp_path / "test.obj"
        f.write_text("dummy")
        info = get_import_info(str(f))
        assert "path" in info
        assert "extension" in info
        assert "format" in info
        assert "method" in info
        assert "exists" in info


class TestListSupportedFormats:
    """Tests for list_supported_formats function."""

    def test_returns_dict(self):
        result = list_supported_formats()
        assert isinstance(result, dict)

    def test_has_mesh_category(self):
        result = list_supported_formats()
        assert "mesh" in result
        assert ".stl" in result["mesh"]

    def test_has_cad_category(self):
        result = list_supported_formats()
        assert "cad" in result
        assert ".step" in result["cad"]

    def test_has_freecad_category(self):
        result = list_supported_formats()
        assert "freecad" in result
        assert ".fcstd" in result["freecad"]

    def test_has_draft_category(self):
        result = list_supported_formats()
        assert "draft" in result
        assert ".dxf" in result["draft"]

    def test_all_extensions_covered(self):
        """All extensions in ALL_EXTENSIONS should be in IMPORT_METHODS."""
        for ext in ALL_EXTENSIONS:
            assert ext in IMPORT_METHODS, f"Extension {ext} not in IMPORT_METHODS"


class TestImportFile:
    """Tests for import_file function."""

    @pytest.fixture
    def mock_backend(self):
        backend = MagicMock()
        backend.document_open.return_value = ToolResponse.ok(
            "document_open", {"name": "Doc", "label": "Doc"}
        )
        backend.execute_code.return_value = ToolResponse.ok(
            "execute_code", {"name": "ImportedMesh", "type": "mesh"}
        )
        return backend

    def test_import_nonexistent_file(self, mock_backend):
        r = import_file(mock_backend, "/nonexistent/model.stl")
        assert r.status == "error"
        assert r.error_code == "FILE_NOT_FOUND"

    def test_import_unknown_format(self, mock_backend, tmp_path):
        f = tmp_path / "model.xyz"
        f.write_text("dummy")
        r = import_file(mock_backend, str(f))
        assert r.status == "error"
        assert r.error_code == "UNKNOWN_FORMAT"

    def test_import_stl(self, mock_backend, tmp_path):
        f = tmp_path / "model.stl"
        f.write_text("solid test")
        r = import_file(mock_backend, str(f))
        assert r.status == "ok"
        mock_backend.execute_code.assert_called_once()

    def test_import_step(self, mock_backend, tmp_path):
        f = tmp_path / "model.step"
        f.write_text("dummy step data")
        r = import_file(mock_backend, str(f))
        assert r.status == "ok"

    def test_import_dxf(self, mock_backend, tmp_path):
        f = tmp_path / "model.dxf"
        f.write_text("dummy dxf")
        r = import_file(mock_backend, str(f))
        assert r.status == "ok"

    def test_import_fcstd(self, mock_backend, tmp_path):
        f = tmp_path / "model.fcstd"
        f.write_bytes(b"dummy fcstd")
        r = import_file(mock_backend, str(f))
        assert r.status == "ok"
        mock_backend.document_open.assert_called_once()

    def test_import_fcstd_merge(self, mock_backend, tmp_path):
        f = tmp_path / "model.fcstd"
        f.write_bytes(b"dummy fcstd")
        r = import_file(mock_backend, str(f), merge=True)
        assert r.status == "ok"
