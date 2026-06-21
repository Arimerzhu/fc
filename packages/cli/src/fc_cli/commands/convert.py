"""Convert commands.

File format conversion utilities that don\'t require a FreeCAD document:
  convert dxf-to-dwg  — Convert DXF to DWG using ODA File Converter
"""

from __future__ import annotations

import os

import click


def _handle_error(f):
    from fc_cli.main import handle_error
    return handle_error(f)


@click.group("convert")
def convert_group():
    """File format conversion utilities."""
    pass


@convert_group.command("dxf-to-dwg")
@click.argument("input", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output DWG path (default: same name with .dwg).")
@click.option("--version", "-v", default="R2018",
              type=click.Choice(["R12", "R13", "R14", "R2000", "R2004", "R2007", "R2010", "R2013", "R2018"]),
              help="DWG version (default: R2018).")
@click.option("--overwrite", is_flag=True, help="Overwrite existing output file.")
@click.option("--no-audit", is_flag=True, help="Skip ODA audit.")
@_handle_error
def convert_dxf_to_dwg(input: str, output: str | None, version: str, overwrite: bool, no_audit: bool) -> None:
    """Convert DXF file to DWG format.

    Uses ODA File Converter (ezdxf odafc) for high-quality conversion.
    Requires ODA File Converter to be installed.

    Examples:
        fc convert dxf-to-dwg drawing.dxf
        fc convert dxf-to-dwg drawing.dxf --output output.dwg --version R2013
        fc convert dxf-to-dwg drawing.dxf --overwrite
    """
    from fc_cli.main import _output
    from fc_core.io.dwg_converter import convert_dwg, is_odafc_available

    if not is_odafc_available():
        _output.error(
            "ODA File Converter not found",
            code="ODAFC_NOT_FOUND",
            suggestion="Install from https://www.opendesign.com/guestfiles/oda_file_converter",
        )
        return

    r = convert_dwg(input, output, version=version, audit=not no_audit, replace=overwrite)
    if r.status == "ok":
        _output.output(r.to_dict(), r.message)
    else:
        _output.error(r.message, code=r.error_code, suggestion=r.suggestion)


@convert_group.command("batch-dxf-to-dwg")
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory (default: same as input).")
@click.option("--version", "-v", default="R2018",
              type=click.Choice(["R12", "R13", "R14", "R2000", "R2004", "R2007", "R2010", "R2013", "R2018"]),
              help="DWG version (default: R2018).")
@click.option("--overwrite", is_flag=True, help="Overwrite existing output files.")
@_handle_error
def convert_batch_dxf_to_dwg(input_dir: str, output_dir: str | None, version: str, overwrite: bool) -> None:
    """Batch convert all DXF files in a directory to DWG.

    Examples:
        fc convert batch-dxf-to-dwg ./dxf_files/
        fc convert batch-dxf-to-dwg ./dxf_files/ --output-dir ./dwg_files/ --version R2013
    """
    from fc_cli.main import _output
    from fc_core.io.dwg_converter import batch_convert, is_odafc_available

    if not is_odafc_available():
        _output.error(
            "ODA File Converter not found",
            code="ODAFC_NOT_FOUND",
            suggestion="Install from https://www.opendesign.com/guestfiles/oda_file_converter",
        )
        return

    results = batch_convert(input_dir, output_dir, version=version, replace=overwrite)
    ok_count = sum(1 for r in results if r.status == "ok")
    fail_count = len(results) - ok_count

    if fail_count == 0:
        _output.output(
            {"converted": ok_count, "failed": 0},
            f"Batch conversion complete: {ok_count} files converted",
        )
    else:
        failed = [r for r in results if r.status != "ok"]
        _output.error(
            f"{fail_count} of {len(results)} conversions failed",
            code="BATCH_PARTIAL",
            suggestion=f"First error: {failed[0].message}",
        )
