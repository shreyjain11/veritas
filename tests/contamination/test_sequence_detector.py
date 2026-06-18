"""SequenceIdentityDetector edge logic (hermetic, via an injected search backend).

Ground truth is planted as backend hits: an exact duplicate (identity 1.0), a
point mutant (0.90), and an unrelated pair (0.20). The detector must turn only
the hits passing the identity/coverage thresholds into edges.
"""

from __future__ import annotations

from veritas.contamination.graph import contaminated_eval_ids
from veritas.contamination.hits import SequenceHit
from veritas.contamination.sequence_identity import SequenceIdentityDetector
from veritas.contracts import (
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    ReferenceItem,
    SeqType,
)


class _FakeSequenceSearch:
    def __init__(self, hits: list[SequenceHit]) -> None:
        self._hits = hits

    def search(
        self,
        eval_items: tuple[EvalItem, ...],
        reference_items: tuple[ReferenceItem, ...],
        *,
        candidate_pairs: set[tuple[str, str]],
    ) -> list[SequenceHit]:
        return list(self._hits)


_HITS = [
    SequenceHit(eval_id="e_dup", ref_id="r1", identity=1.00, coverage=1.00),
    SequenceHit(eval_id="e_mut", ref_id="r2", identity=0.90, coverage=0.95),
    SequenceHit(eval_id="e_unrel", ref_id="r3", identity=0.20, coverage=0.30),
]


def _evals(seq_type: SeqType = SeqType.PROTEIN) -> tuple[EvalItem, ...]:
    seq = "MKVLA" if seq_type is SeqType.PROTEIN else "ACGTA"
    return tuple(
        EvalItem(id=i, sequence=seq, seq_type=seq_type, label=1.0)
        for i in ("e_dup", "e_mut", "e_unrel")
    )


def _refs(seq_type: SeqType = SeqType.PROTEIN) -> tuple[ReferenceItem, ...]:
    seq = "MKVLA" if seq_type is SeqType.PROTEIN else "ACGTA"
    return tuple(ReferenceItem(id=i, sequence=seq, seq_type=seq_type) for i in ("r1", "r2", "r3"))


def _config(identity: float, coverage: float = 0.8) -> DetectorConfig:
    return DetectorConfig(
        kind=DetectorKind.SEQUENCE,
        name="mmseqs",
        identity_threshold=identity,
        coverage_threshold=coverage,
    )


def _detector(hits: list[SequenceHit]) -> SequenceIdentityDetector:
    return SequenceIdentityDetector(search=_FakeSequenceSearch(hits), use_prefilter=False)


def test_golden_high_threshold_recovers_only_exact_duplicate() -> None:
    graph = _detector(_HITS).detect(_evals(), _refs(), _config(identity=0.95))
    assert contaminated_eval_ids(graph) == frozenset({"e_dup"})


def test_golden_lower_threshold_also_recovers_point_mutant() -> None:
    graph = _detector(_HITS).detect(_evals(), _refs(), _config(identity=0.85))
    assert contaminated_eval_ids(graph) == frozenset({"e_dup", "e_mut"})


def test_coverage_threshold_excludes_low_coverage_hit() -> None:
    hits = [SequenceHit(eval_id="e1", ref_id="r1", identity=1.0, coverage=0.4)]
    graph = _detector(hits).detect(_evals(), _refs(), _config(identity=0.9, coverage=0.8))
    assert graph.edges == ()


def test_specificity_uncorrelated_hits_produce_no_edges() -> None:
    # Every pair is unrelated (identity 0.2) -> no spurious edges at a real threshold.
    hits = [
        SequenceHit(eval_id="e1", ref_id="r1", identity=0.2, coverage=0.9),
        SequenceHit(eval_id="e2", ref_id="r2", identity=0.15, coverage=0.9),
    ]
    graph = _detector(hits).detect(_evals(), _refs(), _config(identity=0.9))
    assert graph.edges == ()


def test_supports_nucleotide_alphabet() -> None:
    hits = [SequenceHit(eval_id="e_dup", ref_id="r1", identity=1.0, coverage=1.0)]
    graph = _detector(hits).detect(
        _evals(SeqType.NUCLEOTIDE), _refs(SeqType.NUCLEOTIDE), _config(0.95)
    )
    assert isinstance(graph, ContaminationGraph)
    assert contaminated_eval_ids(graph) == frozenset({"e_dup"})


def test_edges_are_tagged_with_kind_and_detector_id() -> None:
    graph = _detector(_HITS).detect(_evals(), _refs(), _config(identity=0.95))
    edge = graph.edges[0]
    assert edge.kind is DetectorKind.SEQUENCE
    assert edge.detector_id == "mmseqs"
    assert edge.score == 1.0


class _CapturingSearch:
    """Records the candidate pairs handed to the backend; returns no hits."""

    def __init__(self) -> None:
        self.candidate_pairs: set[tuple[str, str]] | None = None

    def search(
        self,
        eval_items: tuple[EvalItem, ...],
        reference_items: tuple[ReferenceItem, ...],
        *,
        candidate_pairs: set[tuple[str, str]],
    ) -> list[SequenceHit]:
        self.candidate_pairs = candidate_pairs
        return []


def test_prefilter_disabled_searches_all_pairs() -> None:
    # With the prefilter off, the backend must receive the full eval x ref product
    # (the detector is exhaustive), which is what correctness tests rely on.
    search = _CapturingSearch()
    detector = SequenceIdentityDetector(search=search, use_prefilter=False)
    detector.detect(_evals(), _refs(), _config(identity=0.9))
    assert search.candidate_pairs == {
        (e, r) for e in ("e_dup", "e_mut", "e_unrel") for r in ("r1", "r2", "r3")
    }


def test_prefilter_enabled_runs_candidate_generation() -> None:
    # Exercises the use_prefilter=True path (MinHash candidate generation). The fake
    # search ignores candidates, so the planted edge is recovered regardless.
    hits = [SequenceHit(eval_id="e_dup", ref_id="r1", identity=1.0, coverage=1.0)]
    detector = SequenceIdentityDetector(search=_FakeSequenceSearch(hits), use_prefilter=True)
    graph = detector.detect(_evals(), _refs(), _config(identity=0.95))
    assert contaminated_eval_ids(graph) == frozenset({"e_dup"})
