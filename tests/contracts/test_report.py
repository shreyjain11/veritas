"""TracedValue, LeakageSummary, AuditReport: provenance enforcement + status (reqs A/B/C)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veritas.contracts import (
    AuditReport,
    LeakageSummary,
    Limitation,
    ProvenanceRecord,
    ResultStatus,
    TracedValue,
)


def _prov() -> ProvenanceRecord:
    return ProvenanceRecord(input_hashes={}, params={}, seed=1, pinned_versions={})


def _traced(value: float | None = 0.8, status: ResultStatus = ResultStatus.OK) -> TracedValue:
    return TracedValue(name="auroc", value=value, status=status, provenance_ref="hash123")


def test_traced_value_requires_provenance_ref() -> None:
    with pytest.raises(ValidationError):
        TracedValue(name="auroc", value=0.8, provenance_ref="")


def test_traced_value_ok_requires_value() -> None:
    with pytest.raises(ValidationError):
        TracedValue(name="auroc", value=None, status=ResultStatus.OK, provenance_ref="h")


def test_traced_value_non_ok_forbids_value() -> None:
    with pytest.raises(ValidationError):
        TracedValue(
            name="auroc",
            value=0.8,
            status=ResultStatus.UNDEFINED_METRIC,
            provenance_ref="h",
        )


def test_traced_value_non_ok_allows_none() -> None:
    tv = TracedValue(
        name="auroc",
        value=None,
        status=ResultStatus.INSUFFICIENT_CLEAN_DATA,
        provenance_ref="h",
    )
    assert tv.value is None


def test_traced_value_ci_ordering() -> None:
    with pytest.raises(ValidationError):
        TracedValue(name="auroc", value=0.8, provenance_ref="h", ci_low=0.9, ci_high=0.7)


def test_leakage_summary_fraction() -> None:
    summary = LeakageSummary(n_eval=10, n_contaminated=2, per_detector={"mmseqs": 2})
    assert summary.fraction_contaminated == pytest.approx(0.2)


def test_leakage_summary_zero_eval_fraction_is_zero() -> None:
    summary = LeakageSummary(n_eval=0, n_contaminated=0, per_detector={})
    assert summary.fraction_contaminated == 0.0


def test_audit_report_requires_audit_hash() -> None:
    with pytest.raises(ValidationError):
        AuditReport(
            audit_hash="",
            benchmark_name="d",
            reported=_traced(),
            honest=_traced(0.7),
            delta=_traced(0.1),
            leakage=LeakageSummary(n_eval=1, n_contaminated=0, per_detector={}),
            provenance=_prov(),
        )


def test_audit_report_round_trip_and_default_status() -> None:
    report = AuditReport(
        audit_hash="deadbeef",
        benchmark_name="d",
        reported=_traced(),
        honest=_traced(0.7),
        delta=_traced(0.1),
        leakage=LeakageSummary(n_eval=10, n_contaminated=2, per_detector={"mmseqs": 2}),
        provenance=_prov(),
    )
    assert report.status is ResultStatus.OK
    assert AuditReport.model_validate_json(report.model_dump_json()) == report


# --- TracedValue unforgeability at the report level -------------------------
# It must be impossible to put an *untraced* number into a report: each metric
# slot accepts only a TracedValue (which itself requires a provenance_ref), so a
# raw float, an untraced dict, or any non-TracedValue is rejected at construction.


def test_audit_report_rejects_raw_float_for_reported() -> None:
    with pytest.raises(ValidationError):
        AuditReport(
            audit_hash="h",
            benchmark_name="d",
            reported=0.8,  # type: ignore[arg-type]  # raw, untraced number
            honest=_traced(0.7),
            delta=_traced(0.1),
            leakage=LeakageSummary(n_eval=1, n_contaminated=0, per_detector={}),
            provenance=_prov(),
        )


def test_audit_report_rejects_untraced_dict_for_honest() -> None:
    with pytest.raises(ValidationError):
        AuditReport(
            audit_hash="h",
            benchmark_name="d",
            reported=_traced(),
            honest={"value": 0.7},  # type: ignore[arg-type]  # dict carries no provenance_ref
            delta=_traced(0.1),
            leakage=LeakageSummary(n_eval=1, n_contaminated=0, per_detector={}),
            provenance=_prov(),
        )


def test_audit_report_rejects_non_traced_value_for_delta() -> None:
    with pytest.raises(ValidationError):
        AuditReport(
            audit_hash="h",
            benchmark_name="d",
            reported=_traced(),
            honest=_traced(0.7),
            delta="0.1",  # type: ignore[arg-type]  # not a TracedValue at all
            leakage=LeakageSummary(n_eval=1, n_contaminated=0, per_detector={}),
            provenance=_prov(),
        )


# --- Limitation + AuditReport.limitations (Phase 5 additive field) -----------


def _report(**overrides: object) -> AuditReport:
    fields: dict[str, object] = dict(
        audit_hash="h",
        benchmark_name="d",
        reported=_traced(),
        honest=_traced(0.7),
        delta=_traced(0.1),
        leakage=LeakageSummary(n_eval=1, n_contaminated=0, per_detector={}),
        provenance=_prov(),
    )
    fields.update(overrides)
    return AuditReport(**fields)  # type: ignore[arg-type]


def test_limitation_requires_all_fields() -> None:
    for bad in ({"id": "", "title": "t", "detail": "d"}, {"id": "x", "title": "", "detail": "d"}):
        with pytest.raises(ValidationError):
            Limitation(**bad)


def test_audit_report_limitations_default_to_empty() -> None:
    assert _report().limitations == ()


def test_audit_report_accepts_and_round_trips_limitations() -> None:
    lim = Limitation(id="bootstrap_small_n", title="Bootstrap under-coverage", detail="...")
    report = _report(limitations=(lim,))
    assert report.limitations == (lim,)
    assert AuditReport.model_validate_json(report.model_dump_json()) == report


def test_audit_report_rejects_non_limitation_entries() -> None:
    with pytest.raises(ValidationError):
        _report(limitations=("not-a-limitation",))
