"""The CI-droppable GitHub Action: declared interface + the leakage-gate behavior."""

from __future__ import annotations

from pathlib import Path

from veritas.audit.gate import evaluate_gate

_ACTION_YML = Path(__file__).resolve().parents[1] / "action.yml"


def _ok_report(reported: float, honest: float) -> dict[str, object]:
    return {
        "reported": {"value": reported, "status": "ok"},
        "honest": {"value": honest, "status": "ok"},
    }


# --- action.yml interface (text assertions; PyYAML is a docs-only extra) ---------


def test_action_declares_its_inputs_and_outputs() -> None:
    text = _ACTION_YML.read_text(encoding="utf-8")
    assert "using: composite" in text
    for declared in ("sequences:", "table:", "reference:", "config:", "max-delta:", "out:"):
        assert declared in text
    assert "report-path:" in text  # an output


def test_action_wires_the_audit_and_the_gate() -> None:
    text = _ACTION_YML.read_text(encoding="utf-8")
    assert "veritas audit" in text
    assert "veritas gate" in text  # the leakage gate is invoked


# --- gate behavior (refinement b: fail loud on non-OK honest) -------------------


def test_gate_passes_when_delta_within_max() -> None:
    passed, _ = evaluate_gate(_ok_report(0.70, 0.65), max_delta=0.1)
    assert passed


def test_gate_fails_when_delta_exceeds_max() -> None:
    passed, message = evaluate_gate(_ok_report(0.90, 0.60), max_delta=0.1)
    assert not passed
    assert "exceeds max" in message


def test_gate_fails_loudly_when_honest_is_insufficient_clean_data() -> None:
    report = {
        "reported": {"value": 0.8, "status": "ok"},
        "honest": {"value": None, "status": "insufficient_clean_data"},
    }
    passed, message = evaluate_gate(report, max_delta=0.1)
    assert not passed  # must NOT silently pass
    assert "insufficient_clean_data" in message


def test_gate_fails_loudly_when_honest_is_undefined_metric() -> None:
    report = {
        "reported": {"value": None, "status": "undefined_metric"},
        "honest": {"value": None, "status": "undefined_metric"},
    }
    passed, message = evaluate_gate(report, max_delta=0.1)
    assert not passed
    assert "undefined_metric" in message


def test_gate_fails_loudly_when_reported_is_undefined_but_honest_is_ok() -> None:
    # Malformed/untrusted input: honest computed but reported is None. Must fail
    # loudly (no TypeError on None - float), not silently certify the model.
    report = {
        "reported": {"value": None, "status": "undefined_metric"},
        "honest": {"value": 0.5, "status": "ok"},
    }
    passed, message = evaluate_gate(report, max_delta=0.1)
    assert not passed
    assert "reported metric" in message
