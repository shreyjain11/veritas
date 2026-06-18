"""Difficulty axes for stratification.

Axes are *read* from artifacts the earlier phases already produced -- never
recomputed. ``identity_to_nearest_reference`` takes its value straight from the
ContaminationGraph edge scores (via ``nearest_score_by_eval``); items with no
edge are maximally dissimilar from the reference set and score ``0.0``.
"""

from __future__ import annotations

from collections.abc import Sequence

from veritas.contamination.graph import nearest_score_by_eval
from veritas.contracts import ContaminationGraph, EvalItem


def identity_to_nearest_reference(
    eval_items: Sequence[EvalItem], graph: ContaminationGraph
) -> dict[str, float]:
    """Per eval id, the score of its closest reference edge (0.0 if none)."""
    nearest = nearest_score_by_eval(graph)
    return {item.id: nearest.get(item.id, 0.0) for item in eval_items}


def label_class(eval_items: Sequence[EvalItem]) -> dict[str, float]:
    """Per eval id, its label -- a categorical difficulty axis."""
    return {item.id: item.label for item in eval_items}
