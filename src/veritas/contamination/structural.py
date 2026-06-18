"""StructuralDetector: contamination via structural similarity (foldseek TM-score)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar, Protocol

from veritas.contamination.base import ContaminationDetector
from veritas.contamination.hits import StructuralHit
from veritas.contracts import (
    ContaminationEdge,
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    ReferenceItem,
    SeqType,
)


class StructuralSearch(Protocol):
    def search(
        self, eval_items: tuple[EvalItem, ...], reference_items: tuple[ReferenceItem, ...]
    ) -> list[StructuralHit]: ...


class StructuralDetector(ContaminationDetector):
    kind: ClassVar[DetectorKind] = DetectorKind.STRUCTURE
    supported_alphabets: ClassVar[frozenset[SeqType]] = frozenset({SeqType.PROTEIN})

    def __init__(self, search: StructuralSearch, *, detector_id: str = "foldseek") -> None:
        self._search = search
        self.detector_id = detector_id
        self.binary_path = getattr(search, "binary_path", None)

    def detect(
        self,
        eval_items: Sequence[EvalItem],
        reference_items: Sequence[ReferenceItem],
        config: DetectorConfig,
    ) -> ContaminationGraph:
        evals = tuple(eval_items)
        refs = tuple(reference_items)
        self._check_alphabets(evals, refs)
        all_items: tuple[EvalItem | ReferenceItem, ...] = (*evals, *refs)
        for item in all_items:
            if item.structure_path is None:
                raise ValueError(
                    f"structural detection requires a structure_path for item {item.id!r}"
                )

        score_t = config.score_threshold if config.score_threshold is not None else 0.0
        edges = tuple(
            ContaminationEdge(
                eval_id=hit.eval_id,
                ref_id=hit.ref_id,
                score=hit.tm_score,
                kind=DetectorKind.STRUCTURE,
                detector_id=self.detector_id,
                details={"tm_score": hit.tm_score},
            )
            for hit in self._search.search(evals, refs)
            if hit.tm_score >= score_t
        )
        return ContaminationGraph(edges=edges)
