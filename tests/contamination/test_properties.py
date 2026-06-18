"""Property-based invariants for the contamination engine (Hypothesis)."""

from __future__ import annotations

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from veritas.contamination.compose import combine
from veritas.contamination.graph import contaminated_eval_ids, intersect, union
from veritas.contamination.hits import SequenceHit
from veritas.contamination.prefilter import DEFAULT_K, _shingles, candidate_pairs
from veritas.contamination.sequence_identity import SequenceIdentityDetector
from veritas.contracts import (
    CombinePolicy,
    ContaminationEdge,
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    ReferenceItem,
    SeqType,
)

_AA = "ACDEFGHIKLMNPQRSTVWY"


class _FakeSearch:
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


def _config(identity: float) -> DetectorConfig:
    return DetectorConfig(
        kind=DetectorKind.SEQUENCE, name="m", identity_threshold=identity, coverage_threshold=0.0
    )


@given(
    identities=st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=1, max_size=8),
    t_low=st.floats(min_value=0.0, max_value=1.0),
    delta=st.floats(min_value=0.0, max_value=1.0),
)
def test_threshold_monotonicity(identities: list[float], t_low: float, delta: float) -> None:
    t_high = min(1.0, t_low + delta)
    hits = [
        SequenceHit(eval_id=f"e{i}", ref_id="r", identity=v, coverage=1.0)
        for i, v in enumerate(identities)
    ]
    evals = tuple(
        EvalItem(id=f"e{i}", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0)
        for i in range(len(identities))
    )
    refs = (ReferenceItem(id="r", sequence="MKV", seq_type=SeqType.PROTEIN),)
    detector = SequenceIdentityDetector(search=_FakeSearch(hits), use_prefilter=False)
    low = contaminated_eval_ids(detector.detect(evals, refs, _config(t_low)))
    high = contaminated_eval_ids(detector.detect(evals, refs, _config(t_high)))
    assert high <= low


_pair = st.tuples(st.sampled_from(["e1", "e2", "e3"]), st.sampled_from(["r1", "r2", "r3"]))


def _graph_from_pairs(pairs: list[tuple[str, str]]) -> ContaminationGraph:
    unique = dict.fromkeys(pairs)
    return ContaminationGraph(
        edges=tuple(
            ContaminationEdge(
                eval_id=e, ref_id=r, score=0.9, kind=DetectorKind.SEQUENCE, detector_id="m"
            )
            for e, r in unique
        )
    )


@given(pairs1=st.lists(_pair, max_size=6), pairs2=st.lists(_pair, max_size=6))
def test_union_equals_set_union_and_intersect_equals_set_intersection(
    pairs1: list[tuple[str, str]], pairs2: list[tuple[str, str]]
) -> None:
    # Equality, not direction: the weaker p1<=u / i<=p1 assertions were passed by a
    # union that returned every pair and an intersect that returned none. Pin both to
    # the exact set operation on the edge (eval_id, ref_id) pairs.
    g1, g2 = _graph_from_pairs(pairs1), _graph_from_pairs(pairs2)
    p1 = {(e.eval_id, e.ref_id) for e in g1.edges}
    p2 = {(e.eval_id, e.ref_id) for e in g2.edges}
    u = {(e.eval_id, e.ref_id) for e in union(g1, g2).edges}
    i = {(e.eval_id, e.ref_id) for e in intersect(g1, g2).edges}
    assert u == p1 | p2
    assert i == p1 & p2


@given(st.lists(st.lists(_pair, max_size=5), min_size=1, max_size=3))
def test_compose_combine_dispatches_to_the_policy_set_op(
    pair_lists: list[list[tuple[str, str]]],
) -> None:
    # compose.combine is the public policy dispatch (UNION/INTERSECT) that the audit
    # pipeline calls; pin it directly to the corresponding set operation over N graphs.
    graphs = [_graph_from_pairs(pl) for pl in pair_lists]
    pair_sets = [{(e.eval_id, e.ref_id) for e in g.edges} for g in graphs]
    u = {(e.eval_id, e.ref_id) for e in combine(graphs, CombinePolicy.UNION).edges}
    i = {(e.eval_id, e.ref_id) for e in combine(graphs, CombinePolicy.INTERSECT).edges}
    assert u == set().union(*pair_sets)
    assert i == set.intersection(*pair_sets)


@given(sequence=st.text(alphabet=_AA, min_size=12, max_size=60))
def test_minhash_recalls_exact_duplicate(sequence: str) -> None:
    evals = (EvalItem(id="e", sequence=sequence, seq_type=SeqType.PROTEIN, label=1.0),)
    refs = (ReferenceItem(id="r", sequence=sequence, seq_type=SeqType.PROTEIN),)
    assert ("e", "r") in candidate_pairs(evals, refs)


def _kmer_jaccard(a: str, b: str) -> float:
    sa, sb = _shingles(a, DEFAULT_K), _shingles(b, DEFAULT_K)
    return len(sa & sb) / len(sa | sb)


#: Recall floor for the LSH prefilter. The MinHash filter is *approximate* (an S-curve,
#: not a step): at the nominal Jaccard threshold (0.5) recall is only ~56%, and the
#: highest Jaccard ever observed to be MISSED across 8k+ pairs was 0.74. We therefore
#: assert deterministic recall only comfortably above that — at the nominal threshold the
#: filter is recall-oriented, not a hard guarantee (see prefilter.py docstring).
_NEAR_DUP_RECALL_MARGIN = 0.80


@st.composite
def _sequence_and_near_duplicate(draw: st.DrawFn) -> tuple[str, str]:
    sequence = draw(st.text(alphabet=_AA, min_size=45, max_size=80))
    n_mut = draw(st.integers(min_value=1, max_value=2))
    positions = draw(
        st.lists(
            st.integers(min_value=0, max_value=len(sequence) - 1),
            min_size=n_mut,
            max_size=n_mut,
            unique=True,
        )
    )
    replacements = draw(
        st.lists(st.sampled_from(_AA), min_size=len(positions), max_size=len(positions))
    )
    chars = list(sequence)
    for pos, char in zip(positions, replacements, strict=True):
        chars[pos] = char
    return sequence, "".join(chars)


@settings(max_examples=150, deadline=None)  # caps cost: each example builds an LSH index
@given(_sequence_and_near_duplicate())
def test_minhash_recalls_high_jaccard_near_duplicates(pair: tuple[str, str]) -> None:
    original, mutated = pair
    assume(mutated != original)  # a genuine near-duplicate, not an exact copy
    assume(_kmer_jaccard(mutated, original) >= _NEAR_DUP_RECALL_MARGIN)
    evals = (EvalItem(id="e", sequence=mutated, seq_type=SeqType.PROTEIN, label=1.0),)
    refs = (ReferenceItem(id="r", sequence=original, seq_type=SeqType.PROTEIN),)
    assert ("e", "r") in candidate_pairs(evals, refs)


def test_detector_is_deterministic() -> None:
    hits = [SequenceHit(eval_id="e1", ref_id="r1", identity=1.0, coverage=1.0)]
    evals = (EvalItem(id="e1", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0),)
    refs = (ReferenceItem(id="r1", sequence="MKV", seq_type=SeqType.PROTEIN),)
    detector = SequenceIdentityDetector(search=_FakeSearch(hits), use_prefilter=False)
    assert detector.detect(evals, refs, _config(0.9)) == detector.detect(evals, refs, _config(0.9))
