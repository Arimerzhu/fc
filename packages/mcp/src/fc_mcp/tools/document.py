"""Document MCP tools: create, open, save, close, info, list."""

from __future__ import annotations

from fc_mcp.server import mcp


def _get_backend(backend_type: str = "headless", freecad_path: str | None = None,
                 host: str = "localhost", port: int = 9875):
    """Get the appropriate backend instance."""
    if backend_type == "rpc":
        from fc_core.backend import RPCBackend
        return RPCBackend(host=host, port=port)
    else:
        from fc_core.backend import HeadlessBackend
        return HeadlessBackend(freecad_path=freecad_path)


@mcp.tool()
def document_new(name: str = "Untitled", backend: str = "headless") -> dict:
    """Create a new FreeCAD document.

    Args:
        name: Document name
        backend: Backend to use ('headless' or 'rpc')
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.document_new(name)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def document_open(file_path: str, backend: str = "headless") -> dict:
    """Open an existing FreeCAD document.

    Args:
        file_path: Path to .FCStd file
        backend: Backend to use ('headless' or 'rpc')
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.document_open(file_path)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def document_save(file_path: str | None = None, backend: str = "headless") -> dict:
    """Save the current document.

    Args:
        file_path: Optional save path (uses current path if not specified)
        backend: Backend to use ('headless' or 'rpc')
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.document_save(file_path)
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def document_info(backend: str = "headless") -> dict:
    """Get information about the current document.

    Args:
        backend: Backend to use ('headless' or 'rpc')
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.document_info()
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def document_close(backend: str = "headless") -> dict:
    """Close the current document.

    Args:
        backend: Backend to use ('headless' or 'rpc')
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.document_close()
        return r.to_dict()
    finally:
        be.disconnect()


@mcp.tool()
def document_list(backend: str = "rpc") -> dict:
    """List open documents (RPC backend only).

    Args:
        backend: Backend to use (must be 'rpc' for this operation)
    """
    be = _get_backend(backend_type=backend)
    try:
        be.connect()
        r = be.object_list()
        return r.to_dict()
    finally:
        be.disconnect()
