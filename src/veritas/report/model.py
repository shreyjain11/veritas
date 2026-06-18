"""Assemble an AuditReport from pipeline outputs, stamping limitations + audit_hash.

The hash is computed over the report's full deterministic content -- INCLUDING the
limitations -- so dropping or changing a disclosed caveat changes ``audit_hash``.
Wall-clock ``created_at`` stamps and the ``audit_hash`` field itself are excluded
so the hash is reproducible and self-consistent.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from veritas.contracts import (
    AuditReport,
    LeakageSummary,
    ProvenanceRecord,
    ResultStatus,
    StratumResult,
    TracedValue,
)
from veritas.provenance import content_hash
from veritas.report.limitations import collect_limitations

# Placeholder hash for the draft; audit_hash_for ignores the stored hash field.
_PENDING_HASH = "pending"


def _traced_payload(traced: TracedValue) -> dict[str, Any]:
    return {
        "name": traced.name,
        "value": traced.value,
        "status": traced.status.value,
        "provenance_ref": traced.provenance_ref,
        "ci_low": traced.ci_low,
        "ci_high": traced.ci_high,
    }


def _hashable_content(report: AuditReport) -> dict[str, Any]:
    provenance = report.provenance
    return {
        "benchmark_name": report.benchmark_name,
        "status": report.status.value,
        "reported": _traced_payload(report.reported),
        "honest": _traced_payload(report.honest),
        "delta": _traced_payload(report.delta),
        "leakage": {
            "n_eval": report.leakage.n_eval,
            "n_contaminated": report.leakage.n_contaminated,
            "per_detector": report.leakage.per_detector,
        },
        "provenance": {
            "input_hashes": provenance.input_hashes,
            "params": provenance.params,
            "seed": provenance.seed,
            "pinned_versions": provenance.pinned_versions,
            "runtime_versions": provenance.runtime_versions,
        },
        "limitations": [
            {"id": lim.id, "title": lim.title, "detail": lim.detail} for lim in report.limitations
        ],
        "stratification": [
            {
                "axis_name": stratum.axis_name,
                "bucket_index": stratum.bucket_index,
                "bucket_label": stratum.bucket_label,
                "n": stratum.n,
                "metric": _traced_payload(stratum.metric),
                "is_silent_failure": stratum.is_silent_failure,
            }
            for stratum in report.stratification
        ],
    }


def audit_hash_for(report: AuditReport) -> str:
    """Deterministic sha256 over the report's content, including its limitations."""
    return content_hash(_hashable_content(report))


def assemble_report(
    *,
    benchmark_name: str,
    reported: TracedValue,
    honest: TracedValue,
    delta: TracedValue,
    leakage: LeakageSummary,
    provenance: ProvenanceRecord,
    prefilter_enabled: bool,
    stratification: Sequence[StratumResult] = (),
    status: ResultStatus = ResultStatus.OK,
    created_at: str | None = None,
) -> AuditReport:
    """Build an AuditReport, collecting limitations and stamping the audit hash.

    Limitations and stratification are populated *before* the hash is stamped, so
    audit_hash covers them (changing a disclosed caveat or a stratum metric changes
    the hash).
    """
    limitations = collect_limitations(prefilter_enabled=prefilter_enabled)
    draft = AuditReport(
        audit_hash=_PENDING_HASH,
        benchmark_name=benchmark_name,
        status=status,
        reported=reported,
        honest=honest,
        delta=delta,
        leakage=leakage,
        provenance=provenance,
        limitations=limitations,
        stratification=tuple(stratification),
        created_at=created_at,
    )
    return draft.model_copy(update={"audit_hash": audit_hash_for(draft)})
