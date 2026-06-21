"""CLI main entry point.

Root command group with global options: --json, --backend, --freecad-path.
"""

from __future__ import annotations

import json
import logging
import sys
from functools import wraps
from typing import Any, Optional

import click

logger = logging.getLogger(__name__)

from fc_cli.output import OutputManager

# Global state
_output: OutputManager = OutputManager()
_backend_type: str = "headless"  # "headless" | "rpc"
_freecad_path: Optional[str] = None
_project_path: Optional[str] = None
_repl_mode: bool = False
_session_name: Optional[str] = None  # 持久化会话名（--session X）


def get_output() -> OutputManager:
    """Get the global output manager."""
    return _output


def get_backend():
    """统一的 backend 获取函数。

    优先级：
    1. --session X：通过 SessionManager 获取该会话的 RPCBackend
    2. --backend rpc：使用 RPCBackend（默认端口 9875）
    3. --backend headless（默认）：使用 HeadlessBackend
    """
    if _session_name:
        from fc_core.session import SessionManager
        mgr = SessionManager()
        return mgr.get_backend(_session_name)
    if _backend_type == "rpc":
        from fc_core.backend import RPCBackend
        return RPCBackend(host="localhost", port=9875)
    from fc_core.backend import HeadlessBackend
    return HeadlessBackend(freecad_path=_freecad_path)


def handle_error(f):
    """Decorator for graceful error handling in CLI and REPL modes."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (FileNotFoundError, ValueError, IndexError,
                RuntimeError, KeyError, TypeError) as e:
            _output.error(str(e), repl_mode=_repl_mode)
    return wrapper


def parse_vec3(s: str) -> list[float]:
    """Parse 'x,y,z' string to [float, float, float]."""
    parts = s.split(",")
    if len(parts) != 3:
        raise ValueError(f"Expected x,y,z format, got: {s}")
    return [float(x.strip()) for x in parts]


def parse_vec2(s: str) -> list[float]:
    """Parse 'x,y' string to [float, float]."""
    parts = s.split(",")
    if len(parts) != 2:
        raise ValueError(f"Expected x,y format, got: {s}")
    return [float(x.strip()) for x in parts]


def parse_params(params: tuple) -> dict[str, float] | None:
    """Parse ('key=value', ...) to dict."""
    if not params:
        return None
    result = {}
    for p in params:
        if "=" not in p:
            raise ValueError(f"Param must be key=value, got: {p}")
        k, v = p.split("=", 1)
        result[k.strip()] = float(v.strip())
    return result


def parse_indices(s: str) -> list[int]:
    """Parse comma-separated int list '1,2,3' to [1, 2, 3]."""
    return [int(x.strip()) for x in s.split(",")]


def parse_points(s: str) -> list[list[float]]:
    """Parse semicolon-separated points 'x,y,z;x,y,z;...' to list of vec3."""
    points = []
    for pt_str in s.split(";"):
        pt_str = pt_str.strip()
        if pt_str:
            points.append(parse_vec3(pt_str))
    return points


def parse_points_2d(s: str) -> list[list[float]]:
    """Parse semicolon-separated 2D points 'x,y;x,y;...'."""
    points = []
    for pt_str in s.split(";"):
        pt_str = pt_str.strip()
        if pt_str:
            points.append(parse_vec2(pt_str))
    return points


@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output in JSON format for AI agents.")
@click.option("--backend", type=click.Choice(["headless", "rpc"]), default="headless",
              help="Backend to use: headless (FreeCADCmd) or rpc (FreeCAD GUI).")
@click.option("--freecad-path", type=click.Path(), default=None,
              help="Path to FreeCAD executable (overrides auto-detection).")
@click.option("--project", "-p", type=click.Path(), default=None,
              help="Project file path for session persistence.")
@click.option("--host", default="localhost", help="RPC host (for rpc backend).")
@click.option("--port", default=9875, type=int, help="RPC port (for rpc backend).")
@click.option("--session", type=str, default=None,
              help="使用指定持久化会话的 RPCBackend（覆盖 --backend）。")
@click.pass_context
def cli(ctx: click.Context, use_json: bool, backend: str, freecad_path: str | None,
        project: str | None, host: str, port: int, session: str | None) -> None:
    """fc — Agent Native FreeCAD CLI

    The most comprehensive AI Agent-friendly FreeCAD command-line tool.
    Supports 258+ commands across all FreeCAD workbenches.

    \b
    Examples:
      fc document new --name "MyPart"
      fc part add box --length 20 --width 15 --height 10
      fc export step --output model.step
      fc agent "设计一个法兰盘"
    """
    global _output, _backend_type, _freecad_path, _project_path, _session_name
    _output = OutputManager(use_json=use_json)
    _backend_type = backend
    _freecad_path = freecad_path
    _project_path = project
    _session_name = session

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ── Import command groups ──
from fc_cli.commands.document import document_group
from fc_cli.commands.part import part_group
from fc_cli.commands.sketch import sketch_group
from fc_cli.commands.body import body_group
from fc_cli.commands.export import export_group
from fc_cli.commands.convert import convert_group
from fc_cli.commands.import_cmd import import_group
from fc_cli.commands.session_cmd import session_group
from fc_cli.commands.execute import execute_group
from fc_cli.commands.mesh import mesh_group
from fc_cli.commands.draft import draft_group
from fc_cli.commands.surface import surface_group
from fc_cli.commands.techdraw import techdraw_group
from fc_cli.commands.spreadsheet import spreadsheet_group
from fc_cli.commands.material import material_group
from fc_cli.commands.assembly import assembly_group
from fc_cli.commands.fem import fem_group
from fc_cli.commands.cam import cam_group

cli.add_command(document_group)
cli.add_command(part_group)
cli.add_command(sketch_group)
cli.add_command(body_group)
cli.add_command(export_group)
cli.add_command(convert_group)
cli.add_command(import_group)
cli.add_command(session_group)
cli.add_command(execute_group)
cli.add_command(mesh_group)
cli.add_command(draft_group)
cli.add_command(surface_group)
cli.add_command(techdraw_group)
cli.add_command(spreadsheet_group)
cli.add_command(material_group)
cli.add_command(assembly_group)
cli.add_command(fem_group)
cli.add_command(cam_group)

# ── REPL command ──
from fc_cli.commands.repl import repl_command
cli.add_command(repl_command)

# ── Load plugins ──
from fc_cli.plugins import load_all_plugins
_plugin_count = load_all_plugins(cli)
if _plugin_count:
    logger.debug(f"Loaded {_plugin_count} plugin(s)")

# ── Agent command (optional, requires fc-runtime) ──
try:
    from fc_runtime.agent_cmd import agent_command
    cli.add_command(agent_command)
except ImportError:
    pass  # fc-runtime not installed


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
