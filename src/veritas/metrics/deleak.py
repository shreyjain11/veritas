"""De-leak policies over a ContaminationGraph: drop, reweight, stratify.

- ``drop`` (default): remove every contaminated eval item.
- ``reweight``: keep all items but down-weight each contaminated item to
  ``1 - max(edge severity)`` — genuinely fractional, distinct from drop.
- ``stratify``: partition into clean/contaminated strata (Phase 4 builds curves
  on top of this).
"""

from __future__ import annotations

from collections.abc import Sequence

from veritas.contracts import ContaminationGraph, EvalItem


def severity_by_eval(graph: ContaminationGraph) -> dict[str, float]:
    """Max contamination score (identity-to-nearest-ref) per eval item."""
    severity: dict[str, float] = {}
    for edge in graph.edges:
        severity[edge.eval_id] = max(severity.get(edge.eval_id, 0.0), edge.score)
    return severity


def drop(eval_items: Sequence[EvalItem], graph: ContaminationGraph) -> tuple[EvalItem, ...]:
    contaminated = severity_by_eval(graph)
    return tuple(item for item in eval_items if item.id not in contaminated)


def reweight(eval_items: Sequence[EvalItem], graph: ContaminationGraph) -> dict[str, float]:
    severity = severity_by_eval(graph)
    return {
        item.id: (1.0 - min(1.0, severity[item.id]) if item.id in severity else 1.0)
        for item in eval_items
    }


def stratify(
    eval_items: Sequence[EvalItem], graph: ContaminationGraph
) -> dict[str, tuple[EvalItem, ...]]:
    contaminated = severity_by_eval(graph)
    return {
        "clean": tuple(item for item in eval_items if item.id not in contaminated),
        "contaminated": tuple(item for item in eval_items if item.id in contaminated),
    }
