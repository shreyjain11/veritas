"""(b) CLI == MCP parity: identical inputs -> identical report + identical audit_hash.

Both paths delegate to the same orchestrator, so the same audit run through
`veritas audit` (CLI) and the MCP `run_audit` tool must produce byte-identical
reports. typer is required for the CLI half (optional `cli` extra).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("typer")

from typer.testing import CliRunner

from tests.factories import PlantedDetector
from tests.mcp import planted_graph, write_audit_fixtures
from veritas.cli import app
from veritas.contamination.registry import register_detector
from veritas.mcp.tools import call_tool

runner = CliRunner()


def test_cli_and_mcp_run_audit_are_identical(tmp_path: Path) -> None:
    register_detector(
        "parity_planted", lambda: PlantedDetector(planted_graph("parity_planted"), "parity_planted")
    )
    write_audit_fixtures(tmp_path, "parity_planted")
    sequences = str(tmp_path / "eval.fasta")
    table = str(tmp_path / "table.csv")
    reference = str(tmp_path / "reference.fasta")
    config = str(tmp_path / "config.json")

    cli_out = tmp_path / "cli_report.json"
    result = runner.invoke(
        app,
        [
            "audit",
            "--sequences",
            sequences,
            "--table",
            table,
            "--reference",
            reference,
            "--config",
            config,
            "--seq-type",
            "protein",
            "--metric",
            "accuracy",
            "--out",
            str(cli_out),
        ],
    )
    assert result.exit_code == 0, result.output
    cli_report = json.loads(cli_out.read_text(encoding="utf-8"))

    mcp_report = call_tool(
        "run_audit",
        {
            "sequences": sequences,
            "table": table,
            "reference": reference,
            "config": config,
            "seq_type": "protein",
            "metric": "accuracy",
        },
    )

    assert mcp_report == cli_report
    assert mcp_report["audit_hash"] == cli_report["audit_hash"]
