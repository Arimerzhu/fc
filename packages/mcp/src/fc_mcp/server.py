"""MCP Server entry point.

Starts the FreeCAD MCP server with all tools registered.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("fc_mcp")


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Server lifecycle management."""
    logger.info("FreeCAD MCP server starting")
    yield {}
    logger.info("FreeCAD MCP server stopped")


mcp = FastMCP(
    "FreeCAD",
    instructions="Agent Native FreeCAD CLI — Control FreeCAD for CAD design tasks.",
    lifespan=server_lifespan,
)


# Import and register all tools
from fc_mcp.tools import document as doc_tools
from fc_mcp.tools import geometry as geo_tools
from fc_mcp.tools import export as export_tools
from fc_mcp.tools import execute as exec_tools
from fc_mcp.tools import sketch as sketch_tools
from fc_mcp.tools import query as query_tools


def main():
    """Run the MCP server."""
    import argparse
    parser = argparse.ArgumentParser(description="FreeCAD MCP Server")
    parser.add_argument("--backend", choices=["headless", "rpc"], default="headless")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9875)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    mcp.run()


if __name__ == "__main__":
    main()
