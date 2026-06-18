"""(b) Hermetic subcommand runs: rescore / stratify on a PRECOMPUTED graph.

rescore and stratify consume an already-computed ContaminationGraph (written to a
file), so they run the de-leak / honest-metric / stratification stages with no
detector and no binary -- fully hermetic. Inputs are generated into tmp_path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("typer")

from typer.testing import CliRunner

from tests.factories import PlantedDetector
from veritas.cli import app
from veritas.contamination.registry import register_detector
from veritas.contracts import (
    AuditConfig,
    ContaminationEdge,
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
)

runner = CliRunner()


def _graph_with_one_edge(detector_id: str) -> ContaminationGraph:
    return ContaminationGraph(
        edges=(
            ContaminationEdge(
                eval_id="a",
                ref_id="r",
                score=1.0,
                kind=DetectorKind.SEQUENCE,
                detector_id=detector_id,
            ),
        )
    )


def _write_inputs(tmp_path: Path) -> None:
    (tmp_path / "eval.fasta").write_text(">a\nMKVLA\n>b\nMKVLC\n", encoding="utf-8")
    (tmp_path / "table.csv").write_text("id,label,prediction\na,1,0.9\nb,1,0.1\n", encoding="utf-8")
    (tmp_path / "graph.json").write_text(
        _graph_with_one_edge("x").model_dump_json(), encoding="utf-8"
    )


def test_rescore_writes_a_report(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    out = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "rescore",
            "--sequences",
            str(tmp_path / "eval.fasta"),
            "--table",
            str(tmp_path / "table.csv"),
            "--graph",
            str(tmp_path / "graph.json"),
            "--seq-type",
            "protein",
            "--metric",
            "accuracy",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "reported" in data and "honest" in data


def test_stratify_writes_a_report(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    out = tmp_path / "strat.json"
    result = runner.invoke(
        app,
        [
            "stratify",
            "--sequences",
            str(tmp_path / "eval.fasta"),
            "--table",
            str(tmp_path / "table.csv"),
            "--graph",
            str(tmp_path / "graph.json"),
            "--seq-type",
            "protein",
            "--metric",
            "accuracy",
            "--axis",
            "identity_to_nearest_reference",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_rescore_rejects_an_unknown_output_format(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    result = runner.invoke(
        app,
        [
            "rescore",
            "--sequences",
            str(tmp_path / "eval.fasta"),
            "--table",
            str(tmp_path / "table.csv"),
            "--graph",
            str(tmp_path / "graph.json"),
            "--seq-type",
            "protein",
            "--metric",
            "accuracy",
            "--out",
            str(tmp_path / "out.xml"),
            "--format",
            "xml",
        ],
    )
    assert result.exit_code != 0  # unknown format -> clean error, not a silent write


def _write_audit_inputs(tmp_path: Path, detector_name: str) -> None:
    (tmp_path / "eval.fasta").write_text(">a\nMKVLA\n>b\nMKVLC\n", encoding="utf-8")
    (tmp_path / "table.csv").write_text("id,label,prediction\na,1,0.9\nb,1,0.1\n", encoding="utf-8")
    (tmp_path / "reference.fasta").write_text(">r\nMKVLA\n", encoding="utf-8")
    config = AuditConfig(
        detectors=(
            DetectorConfig(kind=DetectorKind.SEQUENCE, name=detector_name, identity_threshold=0.5),
        ),
        seed=1729,
    )
    (tmp_path / "config.json").write_text(config.model_dump_json(), encoding="utf-8")


def test_audit_runs_end_to_end_hermetically(tmp_path: Path) -> None:
    # Register a planted detector so `veritas audit` runs the full pipeline with no binary.
    register_detector(
        "cli_planted_audit",
        lambda: PlantedDetector(_graph_with_one_edge("cli_planted_audit"), "cli_planted_audit"),
    )
    _write_audit_inputs(tmp_path, "cli_planted_audit")
    out = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "audit",
            "--sequences",
            str(tmp_path / "eval.fasta"),
            "--table",
            str(tmp_path / "table.csv"),
            "--reference",
            str(tmp_path / "reference.fasta"),
            "--config",
            str(tmp_path / "config.json"),
            "--metric",
            "accuracy",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["benchmark_name"] == "eval"
    assert data["leakage"]["n_contaminated"] == 1


def test_gate_command_passes_within_max_and_fails_over_max(tmp_path: Path) -> None:
    report = {"reported": {"value": 0.9, "status": "ok"}, "honest": {"value": 0.6, "status": "ok"}}
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    within = runner.invoke(app, ["gate", "--report", str(path), "--max-delta", "0.5"])
    assert within.exit_code == 0, within.output
    over = runner.invoke(app, ["gate", "--report", str(path), "--max-delta", "0.1"])
    assert over.exit_code == 1


def test_leakage_writes_a_graph(tmp_path: Path) -> None:
    register_detector(
        "cli_planted_leak",
        lambda: PlantedDetector(_graph_with_one_edge("cli_planted_leak"), "cli_planted_leak"),
    )
    _write_audit_inputs(tmp_path, "cli_planted_leak")
    out = tmp_path / "graph.json"
    result = runner.invoke(
        app,
        [
            "leakage",
            "--sequences",
            str(tmp_path / "eval.fasta"),
            "--reference",
            str(tmp_path / "reference.fasta"),
            "--config",
            str(tmp_path / "config.json"),
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    loaded = ContaminationGraph.model_validate_json(out.read_text(encoding="utf-8"))
    assert len(loaded.edges) == 1
