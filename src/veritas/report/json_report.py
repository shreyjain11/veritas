"""Machine-readable JSON report: deterministic, sorted keys, traceable numbers."""

from __future__ import annotations

import json
from typing import Any

from veritas.contracts import AuditReport, TracedValue


def _traced(traced: TracedValue) -> dict[str, Any]:
    # Value stays a JSON number (json encodes floats with the same shortest repr
    # as numbers.format_number), paired with its provenance_ref and status.
    return {
        "name": traced.name,
        "value": traced.value,
        "status": traced.status.value,
        "provenance_ref": traced.provenance_ref,
        "ci_low": traced.ci_low,
        "ci_high": traced.ci_high,
    }


def render_json(report: AuditReport) -> str:
    provenance = report.provenance
    payload: dict[str, Any] = {
        "audit_hash": report.audit_hash,
        "benchmark_name": report.benchmark_name,
        "status": report.status.value,
        "reported": _traced(report.reported),
        "honest": _traced(report.honest),
        "delta": _traced(report.delta),
        "leakage": {
            "n_eval": report.leakage.n_eval,
            "n_contaminated": report.leakage.n_contaminated,
            "fraction_contaminated": report.leakage.fraction_contaminated,
            "per_detector": report.leakage.per_detector,
        },
        "provenance": {
            "input_hashes": provenance.input_hashes,
            "params": provenance.params,
            "seed": provenance.seed,
            "pinned_versions": provenance.pinned_versions,
            "runtime_versions": provenance.runtime_versions,
            "version_mismatches": list(provenance.version_mismatches),
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
                "metric": _traced(stratum.metric),
                "is_silent_failure": stratum.is_silent_failure,
            }
            for stratum in report.stratification
        ],
        "created_at": report.created_at,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
