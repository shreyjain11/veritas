"""Leakage gate: pass/fail decision from a rendered report + a max allowed delta.

Used by the CI Action's ``max-delta`` gate. It FAILS LOUD (not silently passes) when
the honest metric is undefined (insufficient_clean_data / undefined_metric): you
asked to certify ``reported - honest <= max_delta`` but honest can't be computed, so
the gate cannot vouch for the model and must fail.
"""

from __future__ import annotations

from typing import Any


def evaluate_gate(report: dict[str, Any], max_delta: float) -> tuple[bool, str]:
    """Return ``(passed, message)`` for the leakage gate at ``max_delta``.

    Schema-v2 benchmark-integrity reports gate on the paired robustness gap
    (canonical minus validated-variant accuracy) instead of reported-honest delta.
    """
    if report.get("schema_version") == "2.0":
        return _evaluate_v2_gate(report, max_delta)
    honest = report["honest"]
    if honest.get("status") != "ok" or honest.get("value") is None:
        return False, (
            f"leakage gate FAILED: honest metric is {honest.get('status')!r} "
            f"(value unavailable) — cannot certify reported-honest delta <= {max_delta}"
        )
    reported = report["reported"]
    if reported.get("value") is None:
        return False, (
            f"leakage gate FAILED: reported metric is {reported.get('status')!r} "
            f"(value unavailable) — cannot certify reported-honest delta <= {max_delta}"
        )
    delta = reported["value"] - honest["value"]
    if delta > max_delta:
        return False, (
            f"leakage gate FAILED: reported-honest delta {delta:.6f} exceeds max {max_delta}"
        )
    return True, f"leakage gate passed: reported-honest delta {delta:.6f} <= max {max_delta}"


def _evaluate_v2_gate(report: dict[str, Any], max_delta: float) -> tuple[bool, str]:
    gap = (report.get("score") or {}).get("robustness_gap")
    if not isinstance(gap, int | float):
        return False, (
            "robustness gate FAILED: the report has no paired robustness gap (no validated "
            f"transformations were scored) — cannot certify gap <= {max_delta}"
        )
    if gap > max_delta:
        return False, f"robustness gate FAILED: robustness gap {gap:.6f} exceeds max {max_delta}"
    return True, f"robustness gate passed: robustness gap {gap:.6f} <= max {max_delta}"
