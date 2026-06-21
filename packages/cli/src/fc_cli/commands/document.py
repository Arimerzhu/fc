"""Document management commands.

Commands:
  document new    — Create a new FreeCAD document
  document open   — Open an existing .FCStd file
  document save   — Save the current document
  document info   — Show document information
  document close  — Close the current document
  document list   — List open documents (RPC only)
"""

from __future__ import annotations

import os

import click


def _get_backend():
    """获取 backend 实例（委托给 main.get_backend 统一管理）。"""
    from fc_cli.main import get_backend
    return get_backend()


def _handle_error(f):
    """Decorator for graceful error handling — lazy import to avoid circularity."""
    from fc_cli.main import handle_error
    return handle_error(f)


@click.group("document")
def document_group():
    """Document management commands."""
    pass


@document_group.command("new")
@click.option("--name", "-n", default="Untitled", help="Document name.")
@click.option("--output", "-o", type=click.Path(), help="Save to file after creation.")
@_handle_error
def document_new(name: str, output: str | None) -> None:
    """Create a new FreeCAD document."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.document_new(name)
        if r.status == "ok" and output:
            sr = backend.document_save(output)
            if sr.status == "ok":
                r.data["saved_to"] = os.path.abspath(output)
                r.message = f"Created and saved: {name} → {output}"
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@document_group.command("open")
@click.argument("path", type=click.Path(exists=True))
@_handle_error
def document_open(path: str) -> None:
    """Open an existing FreeCAD document (.FCStd)."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.document_open(path)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@document_group.command("save")
@click.option("--output", "-o", type=click.Path(), help="Save to a new file path.")
@_handle_error
def document_save(output: str | None) -> None:
    """Save the current document."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.document_save(output)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@document_group.command("inject-gui")
@click.option("--output", "-o", type=click.Path(), help="FCStd file path to inject GUI data into.")
@click.option(
    "--view",
    "-v",
    default="isometric",
    type=click.Choice(
        ["isometric", "front", "top", "side", "back", "left", "right"]
    ),
    help="Camera view direction (default: isometric).",
)
@click.option(
    "--fit-all/--no-fit-all",
    default=True,
    help="Auto-fit the model to view (default: yes).",
)
@_handle_error
def document_inject_gui(output: str | None, view: str, fit_all: bool) -> None:
    """Inject GUI view data (camera, ViewProvider, GuiDocument.xml) into a FCStd file.

    用于修复 FreeCADCmd 模式保存的 FCStd 文件在 GUI 中打开时 3D 视图为空的问题。
    必须在 RPC/GUI 会话模式下调用 (使用 --session <name> 或 --backend rpc)。
    """
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.inject_gui_data(output, view=view, fit_all=fit_all)
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@document_group.command("info")
@_handle_error
def document_info() -> None:
    """Show information about the current document."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.document_info()
        _output.output(r.to_dict(), "Document info:")
    finally:
        backend.disconnect()


@document_group.command("close")
@_handle_error
def document_close() -> None:
    """Close the current document."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.document_close()
        _output.output(r.to_dict(), r.message)
    finally:
        backend.disconnect()


@document_group.command("list")
@_handle_error
def document_list() -> None:
    """List open documents (RPC backend only)."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        r = backend.object_list()
        _output.output(r.to_dict(), "Open documents:")
    finally:
        backend.disconnect()
