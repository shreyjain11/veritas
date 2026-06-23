"""Shared view-model for the Markdown and HTML renderers (one source of numbers)."""

from __future__ import annotations

from typing import Any

from veritas.contracts import AuditReport, TracedValue
from veritas.report.numbers import format_number, render_value


def _ci(traced: TracedValue) -> str:
    if traced.value is not None and traced.ci_low is not None and traced.ci_high is not None:
        return f"[{format_number(traced.ci_low)}, {format_number(traced.ci_high)}]"
    return ""


def build_context(report: AuditReport) -> dict[str, Any]:
    # The Markdown/HTML renderers present the reported-vs-honest audit; the wire-format
    # JSON is the renderer for detection / stratification reports.
    reported, honest, delta, leakage = (
        report.reported,
        report.honest,
        report.delta,
        report.leakage,
    )
    if reported is None or honest is None or delta is None or leakage is None:
        raise ValueError(
            f"Markdown/HTML rendering supports metric_audit reports; "
            f"got {report.report_kind.value} (render it as JSON instead)"
        )
    metrics = [
        {
            "label": label,
            "display": render_value(traced),
            "ci": _ci(traced),
            "provenance_ref": traced.provenance_ref,
        }
        for label, traced in (
            ("Reported", reported),
            ("Honest", honest),
            ("Delta", delta),
        )
    ]
    provenance = report.provenance
    return {
        "audit_hash": report.audit_hash,
        "benchmark_name": report.benchmark_name,
        "status": report.status.value.replace("_", " "),
        "metrics": metrics,
        "leakage": {
            "n_eval": leakage.n_eval,
            "n_contaminated": leakage.n_contaminated,
            "fraction": format_number(leakage.fraction_contaminated),
            "per_detector": sorted(leakage.per_detector.items()),
        },
        "seed": provenance.seed,
        "pinned_versions": sorted(provenance.pinned_versions.items()),
        "runtime_versions": sorted(provenance.runtime_versions.items()),
        "version_mismatches": list(provenance.version_mismatches),
        "limitations": [{"title": lim.title, "detail": lim.detail} for lim in report.limitations],
        "stratification": [
            {
                "axis_name": stratum.axis_name,
                "label": stratum.bucket_label,
                "n": stratum.n,
                "display": render_value(stratum.metric),
                "silent_failure": stratum.is_silent_failure,
            }
            for stratum in report.stratification
        ],
    }
