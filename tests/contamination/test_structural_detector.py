"""StructuralDetector edge logic (hermetic, via an injected search backend).

Ground truth is planted as TM-score hits: a near-identical fold (0.95) and an
unrelated fold (0.30). Only hits at/above the TM threshold become edges. The
detector is protein-only and requires a structure for every item.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from veritas.contamination.base import AlphabetError
from veritas.contamination.graph import contaminated_eval_ids
from veritas.contamination.hits import StructuralHit
from veritas.contamination.structural import StructuralDetector
from veritas.contracts import DetectorConfig, DetectorKind, EvalItem, ReferenceItem, SeqType


class _FakeStructuralSearch:
    def __init__(self, hits: list[StructuralHit]) -> None:
        self._hits = hits

    def search(
        self, eval_items: tuple[EvalItem, ...], reference_items: tuple[ReferenceItem, ...]
    ) -> list[StructuralHit]:
        return list(self._hits)


def _evals(
    tmp_path: Path, seq_type: SeqType = SeqType.PROTEIN, *, with_structure: bool = True
) -> tuple[EvalItem, ...]:
    seq = "MKVLA" if seq_type is SeqType.PROTEIN else "ACGTA"
    return tuple(
        EvalItem(
            id=i,
            sequence=seq,
            seq_type=seq_type,
            label=1.0,
            structure_path=(tmp_path / f"{i}.pdb") if with_structure else None,
        )
        for i in ("e_close", "e_far")
    )


def _refs(tmp_path: Path) -> tuple[ReferenceItem, ...]:
    return tuple(
        ReferenceItem(
            id=i, sequence="MKVLA", seq_type=SeqType.PROTEIN, structure_path=tmp_path / f"{i}.pdb"
        )
        for i in ("r1", "r2")
    )


def _config(score: float) -> DetectorConfig:
    return DetectorConfig(kind=DetectorKind.STRUCTURE, name="foldseek", score_threshold=score)


def _detector(hits: list[StructuralHit]) -> StructuralDetector:
    return StructuralDetector(search=_FakeStructuralSearch(hits))


_HITS = [
    StructuralHit(eval_id="e_close", ref_id="r1", tm_score=0.95),
    StructuralHit(eval_id="e_far", ref_id="r2", tm_score=0.30),
]


def test_golden_recovers_only_high_tm_match(tmp_path: Path) -> None:
    graph = _detector(_HITS).detect(_evals(tmp_path), _refs(tmp_path), _config(score=0.5))
    assert contaminated_eval_ids(graph) == frozenset({"e_close"})


def test_specificity_unrelated_folds_produce_no_edges(tmp_path: Path) -> None:
    hits = [
        StructuralHit(eval_id="e_close", ref_id="r1", tm_score=0.30),
        StructuralHit(eval_id="e_far", ref_id="r2", tm_score=0.25),
    ]
    graph = _detector(hits).detect(_evals(tmp_path), _refs(tmp_path), _config(score=0.5))
    assert graph.edges == ()


def test_rejects_nucleotide_alphabet(tmp_path: Path) -> None:
    with pytest.raises(AlphabetError):
        _detector(_HITS).detect(
            _evals(tmp_path, SeqType.NUCLEOTIDE), _refs(tmp_path), _config(score=0.5)
        )


def test_requires_structure_for_every_item(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _detector(_HITS).detect(
            _evals(tmp_path, with_structure=False), _refs(tmp_path), _config(score=0.5)
        )
