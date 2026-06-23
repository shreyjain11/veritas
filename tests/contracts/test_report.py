"""TracedValue, LeakageSummary, AuditReport: provenance enforcement + status (reqs A/B/C)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veritas.contracts import (
    AuditReport,
    DetectorCell,
    LeakageSplit,
    LeakageSummary,
    Limitation,
    ProvenanceRecord,
    ReportKind,
    ResultStatus,
    SplitRole,
    StratumResult,
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


# --- Option B: DetectorCell + LeakageSplit (the detection splits-matrix) ------


def _cell(detector: str = "family", flagged: int = 18, total: int = 52) -> DetectorCell:
    return DetectorCell(
        detector=detector, n_flagged=flagged, n_total=total, threshold_label="Pfam e<=1e-3"
    )


def test_detector_cell_rate_is_computed() -> None:
    assert _cell(flagged=18, total=52).rate == pytest.approx(18 / 52)


def test_detector_cell_zero_total_rate_is_zero() -> None:
    assert _cell(flagged=0, total=0).rate == 0.0


def test_detector_cell_rejects_flagged_exceeding_total() -> None:
    with pytest.raises(ValidationError):
        _cell(flagged=53, total=52)


def test_detector_cell_rejects_negative_counts() -> None:
    with pytest.raises(ValidationError):
        DetectorCell(detector="family", n_flagged=-1, n_total=52, threshold_label="x")


def test_detector_cell_requires_threshold_label() -> None:
    with pytest.raises(ValidationError):
        DetectorCell(detector="family", n_flagged=1, n_total=2, threshold_label="")


def _split(name: str = "demonstration", role: SplitRole = SplitRole.DEMONSTRATION) -> LeakageSplit:
    return LeakageSplit(split_name=name, role=role, cells=(_cell(),))


def test_leakage_split_requires_at_least_one_cell() -> None:
    with pytest.raises(ValidationError):
        LeakageSplit(split_name="s", role=SplitRole.DEMONSTRATION, cells=())


def test_leakage_split_requires_split_name() -> None:
    with pytest.raises(ValidationError):
        LeakageSplit(split_name="", role=SplitRole.CONTROL, cells=(_cell(),))


# --- Option B: report_kind invariants (the no-fabrication validator) ----------


def _stratum() -> StratumResult:
    return StratumResult(
        axis_name="metadata:MSA_Neff_L_category",
        bucket_index=0,
        bucket_label="Low",
        n=15,
        metric=TracedValue(name="spearman", value=0.298, provenance_ref="prov:low"),
    )


def _detection(**overrides: object) -> AuditReport:
    fields: dict[str, object] = dict(
        audit_hash="h",
        benchmark_name="ppi",
        report_kind=ReportKind.DETECTION,
        reported=None,
        honest=None,
        delta=None,
        leakage=None,
        splits=(_split(),),
        provenance=_prov(),
    )
    fields.update(overrides)
    return AuditReport(**fields)  # type: ignore[arg-type]


def _stratification(**overrides: object) -> AuditReport:
    fields: dict[str, object] = dict(
        audit_hash="h",
        benchmark_name="proteingym",
        report_kind=ReportKind.STRATIFICATION,
        reported=None,
        honest=None,
        delta=None,
        leakage=None,
        stratification=(_stratum(),),
        provenance=_prov(),
    )
    fields.update(overrides)
    return AuditReport(**fields)  # type: ignore[arg-type]


def test_default_report_kind_is_metric_audit() -> None:
    assert _report().report_kind is ReportKind.METRIC_AUDIT


def test_detection_report_is_valid_and_round_trips() -> None:
    report = _detection()
    assert report.report_kind is ReportKind.DETECTION
    assert report.reported is None and report.leakage is None
    assert AuditReport.model_validate_json(report.model_dump_json()) == report


def test_stratification_report_is_valid_and_round_trips() -> None:
    report = _stratification()
    assert report.report_kind is ReportKind.STRATIFICATION
    assert AuditReport.model_validate_json(report.model_dump_json()) == report


def test_detection_report_with_a_metric_slot_is_rejected() -> None:
    # The no-fabrication guard (explicit negative case): a non-metric kind must not
    # carry a fabricated metric.
    with pytest.raises(ValidationError):
        _detection(reported=_traced(0.9))


def test_detection_report_with_nonnull_leakage_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _detection(leakage=LeakageSummary(n_eval=1, n_contaminated=0, per_detector={}))


def test_detection_report_requires_at_least_one_split() -> None:
    with pytest.raises(ValidationError):
        _detection(splits=())


def test_stratification_report_requires_at_least_one_stratum() -> None:
    with pytest.raises(ValidationError):
        _stratification(stratification=())


def test_metric_audit_report_requires_its_metric_slots() -> None:
    with pytest.raises(ValidationError):
        _report(reported=None)


def test_metric_audit_report_forbids_splits() -> None:
    with pytest.raises(ValidationError):
        _report(splits=(_split(),))


def test_metric_audit_report_requires_leakage() -> None:
    with pytest.raises(ValidationError):
        _report(leakage=None)


def test_detection_report_forbids_stratification() -> None:
    with pytest.raises(ValidationError):
        _detection(stratification=(_stratum(),))


def test_stratification_report_forbids_splits() -> None:
    with pytest.raises(ValidationError):
        _stratification(splits=(_split(),))
