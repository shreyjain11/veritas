"""IO helpers shared by the CLI and MCP layers (config/graph loading, report writing).

Lives in the audit layer (not cli/) so the MCP tools can reuse it without importing
typer. ``PrecomputedDetector`` lets rescore/stratify reuse the orchestrator on an
already-computed contamination graph -- no detector binary is run.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from veritas.contamination.base import ContaminationDetector
from veritas.contracts import (
    AuditConfig,
    AuditReport,
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    ReferenceItem,
    SeqType,
)
from veritas.report import render_html, render_json, render_markdown

_PLACEHOLDER_SEQUENCE = {SeqType.PROTEIN: "MKV", SeqType.NUCLEOTIDE: "ACGT"}

_RENDERERS = {
    "json": render_json,
    "md": render_markdown,
    "html": render_html,
}


class PrecomputedDetector(ContaminationDetector):
    """Replays an already-computed graph (used by rescore/stratify; runs no binary)."""

    kind = DetectorKind.SEQUENCE
    supported_alphabets = frozenset({SeqType.PROTEIN, SeqType.NUCLEOTIDE})

    def __init__(self, graph: ContaminationGraph) -> None:
        self.detector_id = "precomputed"
        self._graph = graph

    def detect(
        self,
        eval_items: Sequence[EvalItem],
        reference_items: Sequence[ReferenceItem],
        config: DetectorConfig,
    ) -> ContaminationGraph:
        return self._graph


def load_config(path: Path) -> AuditConfig:
    return AuditConfig.model_validate_json(path.read_text(encoding="utf-8"))


def load_graph(path: Path) -> ContaminationGraph:
    return ContaminationGraph.model_validate_json(path.read_text(encoding="utf-8"))


def placeholder_reference(seq_type: SeqType) -> ReferenceItem:
    """A single valid reference item, for commands that operate on a precomputed graph."""
    return ReferenceItem(
        id="precomputed", seq_type=seq_type, sequence=_PLACEHOLDER_SEQUENCE[seq_type]
    )


def write_report(report: AuditReport, out: Path, fmt: str) -> None:
    if fmt not in _RENDERERS:
        raise ValueError(f"unknown format {fmt!r}; choose one of {sorted(_RENDERERS)}")
    out.write_text(_RENDERERS[fmt](report), encoding="utf-8")
