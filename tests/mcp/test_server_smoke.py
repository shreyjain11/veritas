"""(c) Server smoke: the MCP server builds, lists tools, and serves a call end-to-end.

Requires the MCP SDK (optional `mcp` extra); skipped when absent. The server is the
only place the SDK is used. The in-memory client/server harness drives a real
list_tools + call_tool over the protocol (no sockets, no binaries).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("mcp")

import anyio
from mcp.shared.memory import create_connected_server_and_client_session

from tests.factories import PlantedDetector
from tests.mcp import planted_graph, write_audit_fixtures
from veritas.contamination.registry import register_detector
from veritas.mcp.server import build_server, list_tools

_EXPECTED_TOOLS = {"detect_leakage", "rescore", "stratify", "run_audit", "get_provenance"}


def test_build_server_constructs_without_error() -> None:
    assert build_server() is not None


def test_server_lists_all_tools_with_input_schemas() -> None:
    tools = list_tools()
    assert {tool.name for tool in tools} == _EXPECTED_TOOLS
    for tool in tools:
        assert tool.inputSchema  # each tool advertises a JSON input schema
        assert tool.description


def test_in_memory_client_lists_and_calls_tools(tmp_path: Path) -> None:
    register_detector(
        "mcp_inproc", lambda: PlantedDetector(planted_graph("mcp_inproc"), "mcp_inproc")
    )
    write_audit_fixtures(tmp_path, "mcp_inproc")
    server = build_server()

    async def _exercise() -> None:
        async with create_connected_server_and_client_session(server) as client:
            listed = await client.list_tools()
            assert {tool.name for tool in listed.tools} == _EXPECTED_TOOLS

            result = await client.call_tool(
                "run_audit",
                {
                    "sequences": str(tmp_path / "eval.fasta"),
                    "table": str(tmp_path / "table.csv"),
                    "reference": str(tmp_path / "reference.fasta"),
                    "config": str(tmp_path / "config.json"),
                    "seq_type": "protein",
                    "metric": "accuracy",
                },
            )
            payload = json.loads(result.content[0].text)
            assert len(payload["audit_hash"]) == 64

    anyio.run(_exercise)
