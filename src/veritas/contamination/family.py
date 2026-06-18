"""FamilyDetector: contamination via shared profile-HMM family membership (pyhmmer/Pfam)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import ClassVar, Protocol

from veritas.contamination.base import ContaminationDetector
from veritas.contamination.hits import FamilyAssignment
from veritas.contracts import (
    ContaminationEdge,
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    ReferenceItem,
    SeqType,
)


class FamilySearch(Protocol):
    def assign(self, items: tuple[EvalItem | ReferenceItem, ...]) -> list[FamilyAssignment]: ...


def _confidence(eval_evalue: float, ref_evalue: float) -> float:
    # Edge strength = -log10 of the weaker (larger) of the two shared-family E-values,
    # clamped at 0 so the score is always non-negative.
    worst = max(eval_evalue, ref_evalue)
    if worst <= 0.0:  # pragma: no cover - HMMER E-values are always > 0; guards the log10 domain
        return 0.0
    return max(0.0, -math.log10(worst))


class FamilyDetector(ContaminationDetector):
    kind: ClassVar[DetectorKind] = DetectorKind.FAMILY
    supported_alphabets: ClassVar[frozenset[SeqType]] = frozenset({SeqType.PROTEIN})

    def __init__(self, search: FamilySearch, *, detector_id: str = "pyhmmer") -> None:
        self._search = search
        self.detector_id = detector_id

    def detect(
        self,
        eval_items: Sequence[EvalItem],
        reference_items: Sequence[ReferenceItem],
        config: DetectorConfig,
    ) -> ContaminationGraph:
        evals = tuple(eval_items)
        refs = tuple(reference_items)
        self._check_alphabets(evals, refs)

        threshold = config.e_value_threshold if config.e_value_threshold is not None else math.inf
        eval_assign = [a for a in self._search.assign(evals) if a.e_value <= threshold]
        ref_assign = [a for a in self._search.assign(refs) if a.e_value <= threshold]

        refs_by_family: dict[str, list[FamilyAssignment]] = {}
        for assignment in ref_assign:
            refs_by_family.setdefault(assignment.family, []).append(assignment)

        seen: set[tuple[str, str, str]] = set()
        edges: list[ContaminationEdge] = []
        for ev in eval_assign:
            for rf in refs_by_family.get(ev.family, []):
                key = (ev.item_id, rf.item_id, ev.family)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    ContaminationEdge(
                        eval_id=ev.item_id,
                        ref_id=rf.item_id,
                        score=_confidence(ev.e_value, rf.e_value),
                        kind=DetectorKind.FAMILY,
                        detector_id=self.detector_id,
                        details={
                            "family": ev.family,
                            "eval_e_value": ev.e_value,
                            "ref_e_value": rf.e_value,
                        },
                    )
                )
        return ContaminationGraph(edges=tuple(edges))
