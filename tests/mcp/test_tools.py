"""(a/c/d) MCP tool handlers: thin wrappers over audit/, hermetic, with boundary validation.

The five tools are pure-Python handlers (no MCP SDK), dispatched by ``call_tool``.
Each maps to existing audit/pipeline functions:
  detect_leakage -> audit.detect (contamination graph)
  run_audit      -> audit.run_audit (full report)
  rescore        -> audit.run_audit over a precomputed graph (de-leak + honest)
  stratify       -> audit.run_audit over a precomputed graph (+ an axis)
  get_provenance -> reads a report and returns its provenance manifest
Hermetic: a planted detector replaces real binaries; the conftest blocks sockets.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.factories import PlantedDetector
from tests.mcp import planted_graph, write_audit_fixtures, write_graph
from veritas.contamination.registry import register_detector
from veritas.mcp.tools import TOOL_SPECS, call_tool

_EXPECTED_TOOLS = {"detect_leakage", "rescore", "stratify", "run_audit", "get_provenance"}


def _register(name: str) -> None:
    register_detector(name, lambda: PlantedDetector(planted_graph(name), name))


def _audit_args(tmp_path: Path) -> dict[str, str]:
    return {
        "sequences": str(tmp_path / "eval.fasta"),
        "table": str(tmp_path / "table.csv"),
        "reference": str(tmp_path / "reference.fasta"),
        "config": str(tmp_path / "config.json"),
        "seq_type": "protein",
        "metric": "accuracy",
    }


def test_registry_exposes_exactly_the_five_tools() -> None:
    assert {spec.name for spec in TOOL_SPECS} == _EXPECTED_TOOLS


def test_tool_handlers_do_not_require_the_mcp_sdk() -> None:
    # The handlers must be importable/usable without the MCP SDK, so the core tool
    # logic is testable hermetically and the SDK stays confined to server.py.
    probe = "import sys, veritas.mcp.tools; sys.exit(1 if 'mcp' in sys.modules else 0)"
    result = subprocess.run([sys.executable, "-c", probe], capture_output=True, check=False)
    assert result.returncode == 0, result.stderr.decode()


def test_run_audit_tool_returns_a_report(tmp_path: Path) -> None:
    _register("mcp_run")
    write_audit_fixtures(tmp_path, "mcp_run")
    result = call_tool("run_audit", _audit_args(tmp_path))
    assert len(result["audit_hash"]) == 64
    assert "reported" in result and "honest" in result and "stratification" in result


def test_detect_leakage_tool_returns_a_graph(tmp_path: Path) -> None:
    _register("mcp_detect")
    write_audit_fixtures(tmp_path, "mcp_detect")
    args = _audit_args(tmp_path)
    del args["table"], args["metric"]  # detection needs no predictions/metric
    result = call_tool("detect_leakage", args)
    assert result["edges"]  # contamination edges surfaced


def test_rescore_tool_returns_a_report(tmp_path: Path) -> None:
    write_audit_fixtures(tmp_path, "unused")
    write_graph(tmp_path)
    result = call_tool(
        "rescore",
        {
            "sequences": str(tmp_path / "eval.fasta"),
            "table": str(tmp_path / "table.csv"),
            "graph": str(tmp_path / "graph.json"),
            "seq_type": "protein",
            "metric": "accuracy",
        },
    )
    assert "reported" in result and "honest" in result


def test_stratify_tool_returns_stratification(tmp_path: Path) -> None:
    write_audit_fixtures(tmp_path, "unused")
    write_graph(tmp_path)
    result = call_tool(
        "stratify",
        {
            "sequences": str(tmp_path / "eval.fasta"),
            "table": str(tmp_path / "table.csv"),
            "graph": str(tmp_path / "graph.json"),
            "seq_type": "protein",
            "metric": "accuracy",
            "axis": "identity_to_nearest_reference",
        },
    )
    assert result["stratification"]


def test_get_provenance_tool_returns_the_manifest(tmp_path: Path) -> None:
    _register("mcp_prov")
    write_audit_fixtures(tmp_path, "mcp_prov")
    report = call_tool("run_audit", _audit_args(tmp_path))
    (tmp_path / "report.json").write_text(json.dumps(report), encoding="utf-8")
    provenance = call_tool("get_provenance", {"report": str(tmp_path / "report.json")})
    assert "pinned_versions" in provenance and "runtime_versions" in provenance
    assert provenance == report["provenance"]  # consistent with the report it came from


def test_get_provenance_verifies_a_stratified_report(tmp_path: Path) -> None:
    # Exercises report_from_dict's stratification reconstruction: a report WITH strata
    # must round-trip and pass the audit_hash check (not be falsely rejected).
    write_audit_fixtures(tmp_path, "unused")
    write_graph(tmp_path)
    report = call_tool(
        "stratify",
        {
            "sequences": str(tmp_path / "eval.fasta"),
            "table": str(tmp_path / "table.csv"),
            "graph": str(tmp_path / "graph.json"),
            "seq_type": "protein",
            "metric": "accuracy",
            "axis": "identity_to_nearest_reference",
        },
    )
    assert report["stratification"]
    (tmp_path / "report.json").write_text(json.dumps(report), encoding="utf-8")
    provenance = call_tool("get_provenance", {"report": str(tmp_path / "report.json")})
    assert provenance == report["provenance"]


def test_get_provenance_rejects_a_tampered_report(tmp_path: Path) -> None:
    # A report whose body was edited but audit_hash left stale must not yield provenance.
    _register("mcp_tamper")
    write_audit_fixtures(tmp_path, "mcp_tamper")
    report = call_tool("run_audit", _audit_args(tmp_path))
    report["reported"]["value"] = 0.123456  # mutate the body, leave audit_hash unchanged
    (tmp_path / "report.json").write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="audit_hash"):
        call_tool("get_provenance", {"report": str(tmp_path / "report.json")})


# --- (d) boundary validation: malformed args / unknown tool -> clear errors -------


def test_unknown_tool_is_a_clear_error() -> None:
    with pytest.raises(ValueError, match="unknown tool"):
        call_tool("does_not_exist", {})


def test_get_provenance_on_a_malformed_report_is_a_clear_error(tmp_path: Path) -> None:
    # A truncated/hand-written report file -> clear "malformed report", not a raw KeyError.
    (tmp_path / "report.json").write_text(json.dumps({"audit_hash": "x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="malformed report"):
        call_tool("get_provenance", {"report": str(tmp_path / "report.json")})


def test_missing_required_args_raise_validation_error(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        call_tool("run_audit", {"sequences": str(tmp_path / "eval.fasta")})  # missing the rest


def test_bad_enum_arg_raises_validation_error(tmp_path: Path) -> None:
    write_audit_fixtures(tmp_path, "unused")
    args = _audit_args(tmp_path) | {"seq_type": "klingon"}  # not a SeqType
    with pytest.raises(ValidationError):
        call_tool("run_audit", args)
