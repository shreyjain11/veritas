from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veritas.benchmark_integrity.service import audit, inspect_audit, load_spec
from veritas.cli import app


def _spec(tmp_path: Path, *, visibility: str = "public") -> Path:
    items = tmp_path / "items.jsonl"
    items.write_text(
        json.dumps(
            {
                "id": "q1",
                "prompt": "2 + 2?",
                "expected_output": "b",
                "task_type": "multiple_choice",
                "choices": [{"id": "a", "text": "3"}, {"id": "b", "text": "4"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    spec = {
        "schema_version": "2.0",
        "benchmark": {
            "adapter": "jsonl",
            "path": str(items),
            "visibility": visibility,
            "task_type": "multiple_choice",
        },
        "model": {
            "id": "fixture-model",
            "adapter": "replay",
            # The permuted variant moves "4" to label a: a content-tracking model answers a.
            "generation": {"extra": {"responses": {"q1": "b", "q1::choice-order::42": "a"}}},
        },
        "transformations": [{"type": "choice_permutation"}],
        "detectors": [{"type": "perturbation"}, {"type": "exact_match"}, {"type": "probability"}],
        "runtime": {"seed": 42, "reference_texts": ["2 + 2?"]},
    }
    path = tmp_path / "audit.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def test_replay_audit_is_deterministic_and_explicit_about_evidence(tmp_path: Path) -> None:
    spec = load_spec(_spec(tmp_path))
    inspection = inspect_audit(spec)
    assert inspection["estimated_requests"] == 2
    assert inspection["model_capabilities"]["token_probabilities"] is True
    first = audit(spec)
    second = audit(spec)
    assert first.audit_hash == second.audit_hash
    assert first.schema_version == "2.0"
    assert first.score.canonical_reproduced_score == 1.0
    assert first.score.robust_score == 1.0
    assert {finding.detector_id for finding in first.findings} == {
        "perturbation",
        "exact_match",
        "probability",
    }
    assert (
        next(f for f in first.findings if f.detector_id == "probability").status.value == "not_run"
    )


def test_private_external_transfer_requires_explicit_acknowledgement(tmp_path: Path) -> None:
    path = _spec(tmp_path, visibility="private")
    raw = json.loads(path.read_text())
    raw["model"]["adapter"] = "openai_compatible"
    raw["model"]["endpoint"] = "https://example.invalid/v1"
    path.write_text(json.dumps(raw), encoding="utf-8")
    spec = load_spec(path)
    assert inspect_audit(spec)["requires_external_transfer_acknowledgement"] is True
    with pytest.raises(PermissionError):
        audit(spec)


def test_request_limit_is_enforced_before_generation(tmp_path: Path) -> None:
    path = _spec(tmp_path)
    raw = json.loads(path.read_text())
    raw["model"]["request_limit"] = 1
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="request_limit"):
        audit(load_spec(path))


def test_cli_writes_cross_format_v2_audit_package(tmp_path: Path) -> None:
    output = tmp_path / "run"
    result = CliRunner().invoke(
        app,
        ["audit", "--config", str(_spec(tmp_path)), "--out", str(output)],
    )
    assert result.exit_code == 0, result.output
    assert json.loads((output / "report.json").read_text())["schema_version"] == "2.0"
    assert (output / "report.md").read_text().startswith("# Veritas benchmark-integrity")
    assert (output / "report.html").read_text().startswith("<!doctype html>")


def test_cli_audit_prints_a_summary_and_verify_detects_tampering(tmp_path: Path) -> None:
    output = tmp_path / "run"
    runner = CliRunner()
    result = runner.invoke(app, ["audit", "--config", str(_spec(tmp_path)), "--out", str(output)])
    assert result.exit_code == 0, result.output
    assert "canonical 100.0%" in result.output and "audit hash" in result.output
    report = output / "report.json"
    verified = runner.invoke(app, ["verify", "--report", str(report)])
    assert verified.exit_code == 0 and "verified" in verified.output
    data = json.loads(report.read_text())
    data["score"]["canonical_reproduced_score"] = 0.5
    report.write_text(json.dumps(data), encoding="utf-8")
    tampered = runner.invoke(app, ["verify", "--report", str(report)])
    assert tampered.exit_code == 1


def test_cli_turns_configuration_errors_into_one_line(tmp_path: Path) -> None:
    path = _spec(tmp_path)
    raw = json.loads(path.read_text())
    raw["detectors"] = [{"type": "not_a_detector"}]
    path.write_text(json.dumps(raw), encoding="utf-8")
    result = CliRunner().invoke(app, ["inspect", "--config", str(path)])
    assert result.exit_code == 2
    assert "unknown detector(s) not_a_detector" in result.output
    assert "Traceback" not in result.output


def test_cli_lists_registered_detectors_and_adapters() -> None:
    runner = CliRunner()
    assert "template_dependence" in runner.invoke(app, ["detectors"]).output.split()
    assert runner.invoke(app, ["adapters"]).output.split() == [
        "replay",
        "openai_compatible",
        "vllm",
        "huggingface_local",
    ]


def test_cli_gate_accepts_v2_reports(tmp_path: Path) -> None:
    output = tmp_path / "run"
    runner = CliRunner()
    runner.invoke(app, ["audit", "--config", str(_spec(tmp_path)), "--out", str(output)])
    result = runner.invoke(
        app, ["gate", "--report", str(output / "report.json"), "--max-delta", "0.05"]
    )
    assert result.exit_code == 0, result.output
    assert "robustness gate passed" in result.output
