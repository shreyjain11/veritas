"""Enum value contracts (stable string values are part of the serialization API)."""

from __future__ import annotations

from veritas.contracts import (
    CombinePolicy,
    DeLeakPolicy,
    DetectorKind,
    MetricName,
    Partition,
    ReportKind,
    ResultStatus,
    SeqType,
    SplitRole,
)


def test_seq_type_values() -> None:
    assert {s.value for s in SeqType} == {"protein", "nucleotide"}


def test_detector_kind_values() -> None:
    assert {k.value for k in DetectorKind} == {"sequence", "family", "structure"}


def test_deleak_policy_values() -> None:
    assert {p.value for p in DeLeakPolicy} == {"drop", "stratify", "reweight"}


def test_combine_policy_values() -> None:
    assert {c.value for c in CombinePolicy} == {"union", "intersect"}


def test_metric_name_includes_v1_metrics() -> None:
    expected = {"auroc", "auprc", "spearman", "pearson", "accuracy", "mcc", "f1"}
    assert expected <= {m.value for m in MetricName}


def test_result_status_values() -> None:
    assert {r.value for r in ResultStatus} == {
        "ok",
        "insufficient_clean_data",
        "undefined_metric",
    }


def test_partition_values() -> None:
    assert {p.value for p in Partition} == {"train", "eval", "reference"}


def test_report_kind_values() -> None:
    assert {k.value for k in ReportKind} == {"metric_audit", "detection", "stratification"}


def test_split_role_values() -> None:
    assert {r.value for r in SplitRole} == {"demonstration", "control", "finding"}


def test_enums_round_trip_from_string() -> None:
    assert SeqType("protein") is SeqType.PROTEIN
    assert SeqType.PROTEIN.value == "protein"
