"""SequenceIdentityDetector: homology contamination via sequence search (mmseqs/diamond)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar, Protocol

from veritas.contamination.base import ContaminationDetector
from veritas.contamination.hits import SequenceHit
from veritas.contamination.prefilter import candidate_pairs
from veritas.contracts import (
    ContaminationEdge,
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    ReferenceItem,
    SeqType,
)


class SequenceSearch(Protocol):
    def search(
        self,
        eval_items: tuple[EvalItem, ...],
        reference_items: tuple[ReferenceItem, ...],
        *,
        candidate_pairs: set[tuple[str, str]],
    ) -> list[SequenceHit]: ...


class SequenceIdentityDetector(ContaminationDetector):
    kind: ClassVar[DetectorKind] = DetectorKind.SEQUENCE
    supported_alphabets: ClassVar[frozenset[SeqType]] = frozenset(
        {SeqType.PROTEIN, SeqType.NUCLEOTIDE}
    )

    def __init__(
        self, search: SequenceSearch, *, detector_id: str = "mmseqs", use_prefilter: bool = True
    ) -> None:
        self._search = search
        self.detector_id = detector_id
        self._use_prefilter = use_prefilter
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

        if self._use_prefilter:
            candidates = candidate_pairs(evals, refs)
        else:
            candidates = {(e.id, r.id) for e in evals for r in refs}

        identity_t = config.identity_threshold if config.identity_threshold is not None else 0.0
        coverage_t = config.coverage_threshold if config.coverage_threshold is not None else 0.0

        edges = tuple(
            ContaminationEdge(
                eval_id=hit.eval_id,
                ref_id=hit.ref_id,
                score=hit.identity,
                kind=DetectorKind.SEQUENCE,
                detector_id=self.detector_id,
                details={"identity": hit.identity, "coverage": hit.coverage},
            )
            for hit in self._search.search(evals, refs, candidate_pairs=candidates)
            if hit.identity >= identity_t and hit.coverage >= coverage_t
        )
        return ContaminationGraph(edges=edges)
