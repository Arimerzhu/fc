"""Execute commands.

Execute arbitrary Python code or macro files in FreeCAD:
  execute code  — Execute Python code string
  execute file  — Execute a Python macro file
"""

from __future__ import annotations

import os

import click


def _handle_error(f):
    from fc_cli.main import handle_error
    return handle_error(f)


def _get_backend():
    """获取 backend 实例（委托给 main.get_backend 统一管理）。"""
    from fc_cli.main import get_backend
    return get_backend()


@click.group("execute")
def execute_group():
    """Execute Python code or macro files in FreeCAD."""
    pass


@execute_group.command("code")
@click.argument("code")
@click.option("--timeout", default=120, type=int, help="Timeout in seconds.")
@_handle_error
def execute_code(code: str, timeout: int) -> None:
    """Execute arbitrary Python code in FreeCAD.

    The code runs in the FreeCAD Python environment with access to:
    - FreeCAD (document management)
    - Part (geometry)
    - Sketcher (2D sketching)
    - Mesh (mesh operations)
    - And all other FreeCAD modules

    Example:
        fc execute code "print(FreeCAD.ActiveDocument.Name)"
    """
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or "Code executed")
    finally:
        backend.disconnect()


@execute_group.command("file")
@click.argument("path", type=click.Path(exists=True))
@click.option("--timeout", default=120, type=int, help="Timeout in seconds.")
@_handle_error
def execute_file(path: str, timeout: int) -> None:
    """Execute a Python macro file in FreeCAD.

    The file is executed in the FreeCAD Python environment.
    """
    from fc_cli.main import _output
    from fc_core.security import SecurityError, validate_path
    try:
        abs_path = validate_path(path, must_exist=True)
    except (SecurityError, FileNotFoundError) as e:
        _output.error(str(e), code=getattr(e, 'code', 'FILE_NOT_FOUND'))
        return

    backend = _get_backend()
    try:
        backend.connect()
        with open(abs_path, "r", encoding="utf-8") as f:
            code = f.read()
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Executed: {abs_path}")
    finally:
        backend.disconnect()
