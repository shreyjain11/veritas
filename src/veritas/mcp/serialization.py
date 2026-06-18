"""AuditReport / graph <-> plain dict for MCP results (and back, for verification).

``report_to_dict`` reuses the JSON renderer so an MCP result is byte-identical to the
CLI's JSON report (parity). ``report_from_dict`` reconstructs the AuditReport so its
audit_hash can be recomputed and checked (get_provenance integrity).
"""

from __future__ import annotations

import json
from typing import Any

from veritas.contracts import (
    AuditReport,
    ContaminationGraph,
    LeakageSummary,
    Limitation,
    ProvenanceRecord,
    StratumResult,
    TracedValue,
)
from veritas.report import render_json


def report_to_dict(report: AuditReport) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(render_json(report))
    return result


def graph_to_dict(graph: ContaminationGraph) -> dict[str, Any]:
    return graph.model_dump(mode="json")


def _traced(data: dict[str, Any]) -> TracedValue:
    # render_json emits exactly the TracedValue fields, so this round-trips.
    return TracedValue(**data)


def report_from_dict(data: dict[str, Any]) -> AuditReport:
    """Rebuild an AuditReport from its rendered dict (dropping derived display fields).

    Only the hashed/contract fields are restored; derived extras (leakage
    ``fraction_contaminated``, provenance ``version_mismatches``) are recomputed by
    the models and intentionally ignored here. A malformed/truncated report dict
    raises a clear ValueError rather than a cryptic KeyError.
    """
    try:
        leakage = LeakageSummary(
            n_eval=data["leakage"]["n_eval"],
            n_contaminated=data["leakage"]["n_contaminated"],
            per_detector=data["leakage"]["per_detector"],
        )
        prov = data["provenance"]
        provenance = ProvenanceRecord(
            input_hashes=prov["input_hashes"],
            params=prov["params"],
            seed=prov["seed"],
            pinned_versions=prov["pinned_versions"],
            runtime_versions=prov["runtime_versions"],
        )
        limitations = tuple(Limitation(**lim) for lim in data["limitations"])
        stratification = tuple(
            StratumResult(
                axis_name=stratum["axis_name"],
                bucket_index=stratum["bucket_index"],
                bucket_label=stratum["bucket_label"],
                n=stratum["n"],
                metric=_traced(stratum["metric"]),
                is_silent_failure=stratum["is_silent_failure"],
            )
            for stratum in data["stratification"]
        )
        return AuditReport(
            audit_hash=data["audit_hash"],
            benchmark_name=data["benchmark_name"],
            status=data["status"],
            reported=_traced(data["reported"]),
            honest=_traced(data["honest"]),
            delta=_traced(data["delta"]),
            leakage=leakage,
            provenance=provenance,
            limitations=limitations,
            stratification=stratification,
            created_at=data.get("created_at"),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"malformed report: missing or invalid field ({exc})") from exc
