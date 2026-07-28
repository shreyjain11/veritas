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
            "generation": {"extra": {"responses": {"q1": "b", "q1::choice-order::42": "b"}}},
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
