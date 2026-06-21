"""Export presets and advanced export utilities.

Provides high-level export functions with format-specific presets
for common use cases (3D printing, CNC, CAD exchange, visualization).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fc_core.backend import HeadlessBackend
from fc_core.types import ToolResponse


# ── Export Presets ──

EXPORT_PRESETS: dict[str, dict[str, Any]] = {
    "3d_print": {
        "format": "stl",
        "tolerance": 0.05,
        "description": "High-quality STL for 3D printing",
        "angular_deflection": 0.5,
        "relative": False,
    },
    "3d_print_fast": {
        "format": "stl",
        "tolerance": 0.2,
        "description": "Fast STL for 3D printing (lower quality)",
        "angular_deflection": 1.0,
        "relative": False,
    },
    "cad_exchange": {
        "format": "step",
        "description": "STEP AP242 for CAD data exchange",
        "schema": "AP242",
    },
    "cnc": {
        "format": "step",
        "description": "STEP for CNC machining",
        "schema": "AP214",
    },
    "visualization": {
        "format": "obj",
        "description": "OBJ with materials for visualization",
        "export_materials": True,
    },
    "web": {
        "format": "gltf",
        "description": "glTF for web/real-time rendering",
        "embed_images": True,
    },
    "mesh_fine": {
        "format": "stl",
        "tolerance": 0.01,
        "description": "Very fine mesh for simulation",
    },
    "mesh_coarse": {
        "format": "stl",
        "tolerance": 0.5,
        "description": "Coarse mesh for quick preview",
    },
}


def list_presets() -> dict[str, str]:
    """List available export presets with descriptions."""
    return {name: info["description"] for name, info in EXPORT_PRESETS.items()}


def get_preset(name: str) -> dict[str, Any] | None:
    """Get a preset by name."""
    return EXPORT_PRESETS.get(name)


def export_with_preset(
    backend: HeadlessBackend,
    file_path: str,
    preset_name: str,
    overwrite: bool = False,
) -> ToolResponse:
    """Export using a named preset.

    Args:
        backend: Connected backend instance.
        file_path: Output file path.
        preset_name: Name of the export preset.
        overwrite: Whether to overwrite existing files.

    Returns:
        ToolResponse with export result.
    """
    if os.path.exists(file_path) and not overwrite:
        return ToolResponse.error(
            "export",
            "FILE_EXISTS",
            f"File exists: {file_path}",
            suggestion="Use overwrite=True to replace",
        )

    preset = EXPORT_PRESETS.get(preset_name)
    if preset is None:
        return ToolResponse.error(
            "export",
            "UNKNOWN_PRESET",
            f"Unknown preset: {preset_name}",
            suggestion=f"Available: {', '.join(EXPORT_PRESETS.keys())}",
        )

    fmt = preset["format"]
    return backend.export(file_path, fmt)


def export_batch(
    backend: HeadlessBackend,
    output_dir: str,
    base_name: str,
    formats: list[str],
    overwrite: bool = False,
) -> list[ToolResponse]:
    """Export to multiple formats at once.

    Args:
        backend: Connected backend instance.
        output_dir: Output directory.
        base_name: Base filename (without extension).
        formats: List of format extensions (e.g. ["step", "stl", "obj"]).
        overwrite: Whether to overwrite existing files.

    Returns:
        List of ToolResponse, one per format.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for fmt in formats:
        ext = fmt.lstrip(".")
        file_path = os.path.join(output_dir, f"{base_name}.{ext}")
        r = backend.export(file_path, fmt)
        results.append(r)
    return results
