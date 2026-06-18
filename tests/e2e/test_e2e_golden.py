"""(c) End-to-end golden: a small fully-controlled dataset -> a known report.

A hermetic full-pipeline run (planted detector, fake version runner) on the
inflation construction must reproduce the planted reported/honest/delta exactly,
and two independent full runs must produce a byte-identical report and an
identical audit_hash (the determinism contract, PLAN #13).
"""

from __future__ import annotations

import pytest

from tests.factories import make_golden_audit
from veritas.audit import run_audit
from veritas.contracts import AuditReport, ResultStatus
from veritas.report import render_json


def _run() -> AuditReport:
    case = make_golden_audit()
    return run_audit(
        case.config,
        case.inputs,
        detector_factory=case.detector_factory,
        version_runner=case.version_runner,
    )


def test_end_to_end_golden_report_matches_planted_values() -> None:
    case = make_golden_audit()
    report = _run()
    assert report.status is ResultStatus.OK
    assert report.reported.value == pytest.approx(case.expected_reported)  # 0.8
    assert report.honest.value == pytest.approx(case.expected_honest)  # 0.6
    assert report.delta.value == pytest.approx(case.expected_delta)  # 0.2 (float subtraction)
    assert report.leakage.n_eval == 20
    assert report.leakage.n_contaminated == 10


def test_audit_hash_is_deterministic_across_two_full_runs() -> None:
    # Independent runs (fresh inputs), so equality is from content, not identity.
    first, second = _run(), _run()
    assert first.audit_hash == second.audit_hash


def test_two_full_runs_render_byte_identical_reports() -> None:
    # The stronger determinism claim: byte-identical machine artifact (no wall-clock
    # leakage into the report).
    assert render_json(_run()) == render_json(_run())
