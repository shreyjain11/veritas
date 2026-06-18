"""Compose multiple detectors' contamination graphs per a CombinePolicy."""

from __future__ import annotations

from collections.abc import Sequence

from veritas.contamination.graph import intersect, union
from veritas.contracts import CombinePolicy, ContaminationGraph


def combine(graphs: Sequence[ContaminationGraph], policy: CombinePolicy) -> ContaminationGraph:
    if policy is CombinePolicy.UNION:
        return union(*graphs)
    return intersect(*graphs)
