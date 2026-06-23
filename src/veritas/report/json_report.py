"""Machine-readable JSON report: deterministic, sorted keys, traceable numbers."""

from __future__ import annotations

import json
from typing import Any

from veritas.contracts import AuditReport, LeakageSplit, LeakageSummary, TracedValue


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


def _traced_opt(traced: TracedValue | None) -> dict[str, Any] | None:
    return _traced(traced) if traced is not None else None


def _leakage(leakage: LeakageSummary | None) -> dict[str, Any] | None:
    if leakage is None:
        return None
    return {
        "n_eval": leakage.n_eval,
        "n_contaminated": leakage.n_contaminated,
        "fraction_contaminated": leakage.fraction_contaminated,
        "per_detector": leakage.per_detector,
    }


def _splits(splits: tuple[LeakageSplit, ...]) -> list[dict[str, Any]]:
    return [
        {
            "split_name": split.split_name,
            "role": split.role.value,
            "note": split.note,
            "cells": [
                {
                    "detector": cell.detector,
                    "n_flagged": cell.n_flagged,
                    "n_total": cell.n_total,
                    "rate": cell.rate,  # derived (n_flagged / n_total); excluded from the hash
                    "threshold_label": cell.threshold_label,
                }
                for cell in split.cells
            ],
        }
        for split in splits
    ]


def render_json(report: AuditReport) -> str:
    provenance = report.provenance
    payload: dict[str, Any] = {
        "audit_hash": report.audit_hash,
        "benchmark_name": report.benchmark_name,
        "report_kind": report.report_kind.value,
        "status": report.status.value,
        "reported": _traced_opt(report.reported),
        "honest": _traced_opt(report.honest),
        "delta": _traced_opt(report.delta),
        "leakage": _leakage(report.leakage),
        "splits": _splits(report.splits),
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
