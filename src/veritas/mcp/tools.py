"""MCP tool schemas + handlers + dispatch -- pure Python, NO MCP SDK import.

Each tool is a thin wrapper over the shared audit runners (so it is identical to the
CLI). Keeping this module SDK-free lets the tool logic be tested hermetically and
confines the MCP SDK to server.py.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from veritas.audit.runners import audit_from_files, audit_on_precomputed_graph, detect_from_files
from veritas.contracts import MetricName, SeqType
from veritas.mcp.serialization import graph_to_dict, report_from_dict, report_to_dict
from veritas.report import audit_hash_for


class _AuditArgs(BaseModel):
    sequences: Path
    table: Path
    reference: Path
    config: Path
    seq_type: SeqType = SeqType.PROTEIN
    metric: MetricName = MetricName.AUROC


class _DetectArgs(BaseModel):
    sequences: Path
    reference: Path
    config: Path
    seq_type: SeqType = SeqType.PROTEIN


class _RescoreArgs(BaseModel):
    sequences: Path
    table: Path
    graph: Path
    seq_type: SeqType = SeqType.PROTEIN
    metric: MetricName = MetricName.ACCURACY


class _StratifyArgs(_RescoreArgs):
    axis: str = "identity_to_nearest_reference"


class _ProvenanceArgs(BaseModel):
    report: Path


def _run_audit(args: _AuditArgs) -> dict[str, Any]:
    return report_to_dict(
        audit_from_files(
            sequences=args.sequences,
            table=args.table,
            reference=args.reference,
            config=args.config,
            seq_type=args.seq_type,
            metric=args.metric,
        )
    )


def _detect_leakage(args: _DetectArgs) -> dict[str, Any]:
    return graph_to_dict(
        detect_from_files(
            sequences=args.sequences,
            reference=args.reference,
            config=args.config,
            seq_type=args.seq_type,
        )
    )


def _rescore(args: _RescoreArgs) -> dict[str, Any]:
    return report_to_dict(
        audit_on_precomputed_graph(
            sequences=args.sequences,
            table=args.table,
            graph=args.graph,
            seq_type=args.seq_type,
            metric=args.metric,
            axes=(),
        )
    )


def _stratify(args: _StratifyArgs) -> dict[str, Any]:
    return report_to_dict(
        audit_on_precomputed_graph(
            sequences=args.sequences,
            table=args.table,
            graph=args.graph,
            seq_type=args.seq_type,
            metric=args.metric,
            axes=(args.axis,),
        )
    )


def _get_provenance(args: _ProvenanceArgs) -> dict[str, Any]:
    report_dict: dict[str, Any] = json.loads(args.report.read_text(encoding="utf-8"))
    report = report_from_dict(report_dict)
    # Refuse to vouch for provenance from a report whose hash no longer matches its body.
    if audit_hash_for(report) != report.audit_hash:
        raise ValueError("report audit_hash does not match its content; provenance is stale")
    provenance: dict[str, Any] = report_dict["provenance"]
    return provenance


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[Any], dict[str, Any]]


TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "detect_leakage",
        "Detect cross-set contamination; returns a graph.",
        _DetectArgs,
        _detect_leakage,
    ),
    ToolSpec(
        "rescore", "Reported-vs-honest metric on a precomputed graph.", _RescoreArgs, _rescore
    ),
    ToolSpec("stratify", "Stratified robustness on a precomputed graph.", _StratifyArgs, _stratify),
    ToolSpec("run_audit", "Run the full audit pipeline; returns a report.", _AuditArgs, _run_audit),
    ToolSpec(
        "get_provenance",
        "Return a report's provenance (hash-verified).",
        _ProvenanceArgs,
        _get_provenance,
    ),
)

_SPECS_BY_NAME = {spec.name: spec for spec in TOOL_SPECS}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Validate arguments at the MCP boundary and dispatch to the handler."""
    spec = _SPECS_BY_NAME.get(name)
    if spec is None:
        raise ValueError(f"unknown tool: {name!r}; available: {sorted(_SPECS_BY_NAME)}")
    args = spec.args_model.model_validate(arguments)
    return spec.handler(args)
