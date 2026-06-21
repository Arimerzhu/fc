"""DXF to DWG converter using ODA File Converter via ezdxf.

Provides a clean, non-GUI interface for converting DXF files to DWG format.
Uses the ezdxf.addons.odafc module which calls ODA File Converter in the
background without any GUI automation.

Requirements:
    - ezdxf >= 1.4 (already a project dependency)
    - ODA File Converter installed

Usage:
    from fc_core.io.dwg_converter import convert_dwg, is_odafc_available
    if is_odafc_available():
        result = convert_dwg("input.dxf", "output.dwg", version="R2018")
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from fc_core.types import ToolResponse

logger = logging.getLogger(__name__)

_ODA_PATH_CACHE: str | None = None


def _find_odafc() -> str | None:
    """Locate ODA File Converter executable."""
    global _ODA_PATH_CACHE
    if _ODA_PATH_CACHE and os.path.isfile(_ODA_PATH_CACHE):
        return _ODA_PATH_CACHE

    try:
        import ezdxf
        configured = ezdxf.options.get("odafc-addon", "win_exec_path").strip('" ')
        if configured and os.path.isfile(configured):
            _ODA_PATH_CACHE = configured
            return configured
    except Exception:
        pass

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    search_dirs = [
        os.path.join(program_files, "ODA"),
        os.path.join(program_files_x86, "ODA"),
        os.path.join(program_files, "Open Design Alliance"),
    ]
    for base in search_dirs:
        if not os.path.isdir(base):
            continue
        for entry in sorted(os.listdir(base), reverse=True):
            if "ODAFileConverter" in entry or "ODA" in entry:
                candidate = os.path.join(base, entry, "ODAFileConverter.exe")
                if os.path.isfile(candidate):
                    _ODA_PATH_CACHE = candidate
                    return candidate

    path_result = shutil.which("ODAFileConverter")
    if path_result:
        _ODA_PATH_CACHE = path_result
        return path_result
    return None


def is_odafc_available() -> bool:
    """Check if ODA File Converter is available."""
    return _find_odafc() is not None


def get_odafc_path() -> str:
    """Get ODA File Converter path, raising if not found."""
    path = _find_odafc()
    if path is None:
        raise FileNotFoundError(
            "ODA File Converter not found. "
            "Install from https://www.opendesign.com/guestfiles/oda_file_converter"
        )
    return path


DWG_VERSIONS: dict[str, str] = {
    "R12": "ACAD12", "R13": "ACAD13", "R14": "ACAD14",
    "R2000": "ACAD2000", "R2004": "ACAD2004", "R2007": "ACAD2007",
    "R2010": "ACAD2010", "R2013": "ACAD2013", "R2018": "ACAD2018",
}
_DEFAULT_VERSION = "R2018"


def _resolve_version(version: str | None) -> str:
    """Resolve version string to ODAFC-compatible format."""
    if version is None:
        return _DEFAULT_VERSION
    v = version.upper().strip()
    if v.startswith("ACAD"):
        return v
    if v in DWG_VERSIONS:
        return DWG_VERSIONS[v]
    v2 = "R" + v
    if v2 in DWG_VERSIONS:
        return DWG_VERSIONS[v2]
    logger.warning("Unknown DWG version '%s', using %s", version, _DEFAULT_VERSION)
    return _DEFAULT_VERSION


def convert_dwg(
    source: str | os.PathLike,
    dest: str | os.PathLike | None = None,
    *,
    version: str | None = None,
    audit: bool = True,
    replace: bool = False,
) -> ToolResponse:
    """Convert DXF file to DWG format using ODA File Converter.

    Non-GUI conversion via ezdxf odafc addon.

    Args:
        source: Path to input DXF file.
        dest: Path to output DWG file. If None, uses source path with .dwg extension.
        version: Target DWG version (R12-R2018). Defaults to R2018.
        audit: Run ODA audit on the output file.
        replace: Overwrite existing output file.

    Returns:
        ToolResponse with conversion result.
    """
    source = Path(source).resolve()
    if not source.is_file():
        return ToolResponse.error(
            "convert_dwg", "FILE_NOT_FOUND",
            f"Source file not found: {source}",
        )

    if dest is None:
        dest = source.with_suffix(".dwg")
    else:
        dest = Path(dest).resolve()

    if dest.is_file() and not replace:
        return ToolResponse.error(
            "convert_dwg", "FILE_EXISTS",
            f"Output file exists: {dest}",
            suggestion="Use replace=True to overwrite",
        )

    os.makedirs(str(dest.parent), exist_ok=True)
    odaf_version = _resolve_version(version)
    t0 = time.time()

    # Try ezdxf odafc first
    try:
        result = _convert_via_ezdxf(str(source), str(dest), odaf_version, audit)
        elapsed = time.time() - t0
        if result:
            file_size = os.path.getsize(dest) if dest.is_file() else 0
            return ToolResponse.ok(
                "convert_dwg",
                {
                    "output": str(dest), "format": "dwg",
                    "version": odaf_version, "file_size": file_size,
                    "elapsed_sec": round(elapsed, 2), "method": "ezdxf_odafc",
                },
                f"Converted DXF->DWG: {dest.name} ({file_size:,} bytes, {elapsed:.1f}s)",
            )
    except Exception as e:
        logger.warning("ezdxf odafc conversion failed: %s, trying fallback", e)

    # Fallback: direct subprocess
    try:
        result = _convert_via_subprocess(str(source), str(dest), odaf_version)
        elapsed = time.time() - t0
        if result and dest.is_file():
            file_size = os.path.getsize(dest)
            return ToolResponse.ok(
                "convert_dwg",
                {
                    "output": str(dest), "format": "dwg",
                    "version": odaf_version, "file_size": file_size,
                    "elapsed_sec": round(elapsed, 2), "method": "subprocess",
                },
                f"Converted DXF->DWG: {dest.name} ({file_size:,} bytes, {elapsed:.1f}s)",
            )
    except Exception as e:
        logger.error("Subprocess conversion also failed: %s", e)

    return ToolResponse.error(
        "convert_dwg", "CONVERSION_FAILED",
        f"Failed to convert {source.name} to DWG",
        suggestion="Ensure ODA File Converter is installed and the DXF file is valid",
    )


def _convert_via_ezdxf(source: str, dest: str, version: str, audit: bool) -> bool:
    """Convert using ezdxf.addons.odafc."""
    import ezdxf
    from ezdxf.addons import odafc

    oda_path = _find_odafc()
    if oda_path:
        ezdxf.options.set("odafc-addon", "win_exec_path", '"' + oda_path + '"')

    if not odafc.is_installed():
        raise RuntimeError("ODA File Converter not detected by ezdxf")

    odafc.convert(source, dest, version=version, audit=audit, replace=True)
    return os.path.isfile(dest) and os.path.getsize(dest) > 0


def _convert_via_subprocess(source: str, dest: str, version: str) -> bool:
    """Convert using direct subprocess call to ODA File Converter."""
    oda_path = get_odafc_path()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ini", delete=False, encoding="utf-8"
    ) as ini:
        ini.write("[Settings]\n")
        ini.write(f"InputFile={source}\n")
        ini.write(f"OutputFile={dest}\n")
        ini.write("OutputFormat=DWG\n")
        ini.write(f"Version={version}\n")
        ini_path = ini.name

    try:
        result = subprocess.run(
            [oda_path, "/ini", ini_path],
            capture_output=True, text=True, timeout=120,
            cwd=os.path.dirname(oda_path),
        )
        if result.returncode == 0 and os.path.isfile(dest):
            return True

        result = subprocess.run(
            [oda_path, source, dest],
            capture_output=True, text=True, timeout=120,
            cwd=os.path.dirname(oda_path),
        )
        return os.path.isfile(dest) and os.path.getsize(dest) > 0
    finally:
        os.unlink(ini_path)


def batch_convert(
    source_dir: str | os.PathLike,
    output_dir: str | os.PathLike | None = None,
    *,
    version: str | None = None,
    replace: bool = False,
) -> list[ToolResponse]:
    """Convert all DXF files in a directory to DWG."""
    source_dir = Path(source_dir)
    if output_dir is None:
        output_dir = source_dir
    else:
        output_dir = Path(output_dir)
        os.makedirs(str(output_dir), exist_ok=True)

    results = []
    for dxf_file in sorted(source_dir.glob("*.dxf")):
        dest = output_dir / dxf_file.with_suffix(".dwg").name
        r = convert_dwg(dxf_file, dest, version=version, replace=replace)
        results.append(r)
    return results
