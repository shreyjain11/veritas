"""ContaminationDetector interface: kind/alphabet metadata and the alphabet guard."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from veritas.contamination.base import AlphabetError, ContaminationDetector
from veritas.contracts import (
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    ReferenceItem,
    SeqType,
)


class _ProteinOnlyDetector(ContaminationDetector):
    kind = DetectorKind.STRUCTURE
    supported_alphabets = frozenset({SeqType.PROTEIN})
    detector_id = "fake"

    def detect(
        self,
        eval_items: Sequence[EvalItem],
        reference_items: Sequence[ReferenceItem],
        config: DetectorConfig,
    ) -> ContaminationGraph:
        self._check_alphabets(eval_items, reference_items)
        return ContaminationGraph(edges=())


def _eval(seq_type: SeqType, sequence: str) -> EvalItem:
    return EvalItem(id="e1", sequence=sequence, seq_type=seq_type, label=1.0)


def _ref(seq_type: SeqType, sequence: str) -> ReferenceItem:
    return ReferenceItem(id="r1", sequence=sequence, seq_type=seq_type)


def test_detector_exposes_kind_and_alphabets() -> None:
    detector = _ProteinOnlyDetector()
    assert detector.kind is DetectorKind.STRUCTURE
    assert detector.supported_alphabets == frozenset({SeqType.PROTEIN})


def test_check_alphabets_accepts_supported() -> None:
    detector = _ProteinOnlyDetector()
    config = DetectorConfig(kind=DetectorKind.STRUCTURE, name="fake", score_threshold=0.5)
    graph = detector.detect(
        (_eval(SeqType.PROTEIN, "MKV"),), (_ref(SeqType.PROTEIN, "MKV"),), config
    )
    assert graph.edges == ()


def test_check_alphabets_rejects_unsupported_alphabet() -> None:
    detector = _ProteinOnlyDetector()
    config = DetectorConfig(kind=DetectorKind.STRUCTURE, name="fake", score_threshold=0.5)
    with pytest.raises(AlphabetError):
        detector.detect(
            (_eval(SeqType.NUCLEOTIDE, "ACGT"),), (_ref(SeqType.PROTEIN, "MKV"),), config
        )
