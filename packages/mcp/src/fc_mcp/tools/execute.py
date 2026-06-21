"""Execute MCP tools: execute Python code or macro files."""

from __future__ import annotations

import os

from fc_mcp.server import mcp


def _get_backend(backend_type: str = "headless", freecad_path: str | None = None,
                 host: str = "localhost", port: int = 9875):
    if backend_type == "rpc":
        from fc_core.backend import RPCBackend
        return RPCBackend(host=host, port=port)
    else:
        from fc_core.backend import HeadlessBackend
        return HeadlessBackend(freecad_path=freecad_path)


@mcp.tool()
def execute_code(code: str, backend: str = "headless", timeout: int = 120) -> dict:
    """Execute arbitrary Python code in the FreeCAD environment.

    Args:
        code: Python code to execute
        backend: Backend to use
        timeout: Execution timeout in seconds
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def execute_file(file_path: str, backend: str = "headless", timeout: int = 120) -> dict:
    """Execute a Python macro file in the FreeCAD environment.

    Args:
        file_path: Path to the .py macro file
        backend: Backend to use
        timeout: Execution timeout in seconds
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        abs_path = os.path.abspath(file_path)
        if not os.path.isfile(abs_path):
            from fc_core.types import ToolResponse
            return ToolResponse.error("execute_file", "FILE_NOT_FOUND",
                                      f"File not found: {file_path}").to_dict()
        with open(abs_path, "r", encoding="utf-8") as f:
            code = f.read()
        r = be.execute_code(code)
        return r.to_dict()
    finally:
        be.disconnect()
