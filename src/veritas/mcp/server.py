"""The MCP server over stdio -- the ONLY module that imports the MCP SDK.

Structured so HTTP/SSE could be added without touching tool logic: all tools come
from veritas.mcp.tools (SDK-free); this layer only adapts them to the SDK.
"""

from __future__ import annotations

import json
from typing import Any

import mcp.types as types
from mcp.server import Server

from veritas.mcp.tools import TOOL_SPECS, call_tool


def list_tools() -> list[types.Tool]:
    """The MCP tool descriptors, with JSON input schemas from the arg models."""
    return [
        types.Tool(
            name=spec.name,
            description=spec.description,
            inputSchema=spec.args_model.model_json_schema(),
        )
        for spec in TOOL_SPECS
    ]


def build_server() -> Server:
    server: Server = Server("veritas")

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return list_tools()

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
        result = call_tool(name, arguments or {})
        return [types.TextContent(type="text", text=json.dumps(result))]

    return server


def run() -> None:  # pragma: no cover - stdio event loop; not exercised in hermetic tests
    import anyio
    from mcp.server.stdio import stdio_server

    async def _main() -> None:
        server = build_server()
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    anyio.run(_main)
