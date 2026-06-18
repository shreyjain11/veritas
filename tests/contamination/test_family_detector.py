"""FamilyDetector: shared-family edge logic plus a real in-process pyhmmer golden.

The injected-backend tests pin the edge logic deterministically (an edge exists
iff an eval and a ref share a family with both E-values within threshold). The
pyhmmer golden runs the actual profile HMM in-process (no external binary) on a
vendored seed alignment, recovering a planted family member and rejecting a decoy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from veritas.contamination.backends.pyhmmer_search import PyhmmerSearch
from veritas.contamination.base import AlphabetError
from veritas.contamination.family import FamilyDetector
from veritas.contamination.graph import contaminated_eval_ids
from veritas.contamination.hits import FamilyAssignment
from veritas.contracts import DetectorConfig, DetectorKind, EvalItem, ReferenceItem, SeqType

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "contamination"
_MEMBER = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKA"
_DECOY = "WWWWCCCCDDDDEEEEFFFFGGGGHHHHIIIIKKKKLLLLMMMMNNNNPPPPQQQQRRRRSS"


class _FakeFamilySearch:
    def __init__(self, assignments: list[FamilyAssignment]) -> None:
        self._assignments = assignments

    def assign(self, items: tuple[EvalItem | ReferenceItem, ...]) -> list[FamilyAssignment]:
        ids = {item.id for item in items}
        return [a for a in self._assignments if a.item_id in ids]


def _evals(seq_type: SeqType = SeqType.PROTEIN) -> tuple[EvalItem, ...]:
    seq = "MKVLA" if seq_type is SeqType.PROTEIN else "ACGTA"
    return (
        EvalItem(id="e1", sequence=seq, seq_type=seq_type, label=1.0),
        EvalItem(id="e2", sequence=seq, seq_type=seq_type, label=0.0),
    )


def _refs() -> tuple[ReferenceItem, ...]:
    return (
        ReferenceItem(id="r1", sequence="MKVLA", seq_type=SeqType.PROTEIN),
        ReferenceItem(id="r3", sequence="MKVLA", seq_type=SeqType.PROTEIN),
    )


def _config(e_value: float = 1e-5) -> DetectorConfig:
    return DetectorConfig(kind=DetectorKind.FAMILY, name="pyhmmer", e_value_threshold=e_value)


def test_golden_shared_family_within_threshold_yields_edge() -> None:
    assignments = [
        FamilyAssignment(item_id="e1", family="FamA", e_value=1e-30),
        FamilyAssignment(item_id="r1", family="FamA", e_value=1e-25),
        FamilyAssignment(item_id="e2", family="FamB", e_value=1e-20),
        FamilyAssignment(item_id="r3", family="FamC", e_value=1e-20),
    ]
    graph = FamilyDetector(search=_FakeFamilySearch(assignments)).detect(
        _evals(), _refs(), _config()
    )
    assert contaminated_eval_ids(graph) == frozenset({"e1"})


def test_specificity_no_shared_family_yields_no_edges() -> None:
    assignments = [
        FamilyAssignment(item_id="e1", family="FamA", e_value=1e-30),
        FamilyAssignment(item_id="r1", family="FamZ", e_value=1e-30),
    ]
    graph = FamilyDetector(search=_FakeFamilySearch(assignments)).detect(
        _evals(), _refs(), _config()
    )
    assert graph.edges == ()


def test_assignment_above_evalue_threshold_is_excluded() -> None:
    assignments = [
        FamilyAssignment(item_id="e1", family="FamA", e_value=1e-3),  # weaker than threshold
        FamilyAssignment(item_id="r1", family="FamA", e_value=1e-25),
    ]
    graph = FamilyDetector(search=_FakeFamilySearch(assignments)).detect(
        _evals(), _refs(), _config(e_value=1e-5)
    )
    assert graph.edges == ()


# --- e-value boundary: the threshold must be applied PER HIT, not "shared family" ---
# threshold = 1e-5; one assignment just below (passes), one just above (the
# "just-below-threshold family analogue of the decoy" -> must fail).
_EVALUE_THRESHOLD = 1e-5
_JUST_BELOW = 9e-6  # < threshold -> passes
_JUST_ABOVE = 2e-5  # > threshold -> fails


def test_evalue_boundary_one_side_above_threshold_yields_no_edge() -> None:
    # Same family, both hit it, but the ref's hit is just above threshold -> no edge.
    assignments = [
        FamilyAssignment(item_id="e1", family="FamA", e_value=_JUST_BELOW),
        FamilyAssignment(item_id="r1", family="FamA", e_value=_JUST_ABOVE),
    ]
    graph = FamilyDetector(search=_FakeFamilySearch(assignments)).detect(
        _evals(), _refs(), _config(e_value=_EVALUE_THRESHOLD)
    )
    assert graph.edges == ()


def test_evalue_boundary_both_below_threshold_yields_edge() -> None:
    # Identical setup except the ref hit is now just below threshold -> edge appears,
    # proving the no-edge case above is driven by the per-hit threshold, not the family.
    assignments = [
        FamilyAssignment(item_id="e1", family="FamA", e_value=_JUST_BELOW),
        FamilyAssignment(item_id="r1", family="FamA", e_value=_JUST_BELOW),
    ]
    graph = FamilyDetector(search=_FakeFamilySearch(assignments)).detect(
        _evals(), _refs(), _config(e_value=_EVALUE_THRESHOLD)
    )
    assert contaminated_eval_ids(graph) == frozenset({"e1"})


def test_rejects_nucleotide_alphabet() -> None:
    detector = FamilyDetector(search=_FakeFamilySearch([]))
    with pytest.raises(AlphabetError):
        detector.detect(_evals(SeqType.NUCLEOTIDE), _refs(), _config())


def test_duplicate_ref_assignments_yield_single_edge() -> None:
    # A backend returning the same family assignment twice must not double-count.
    assignments = [
        FamilyAssignment(item_id="e1", family="FamA", e_value=1e-30),
        FamilyAssignment(item_id="r1", family="FamA", e_value=1e-25),
        FamilyAssignment(item_id="r1", family="FamA", e_value=1e-25),
    ]
    graph = FamilyDetector(search=_FakeFamilySearch(assignments)).detect(
        _evals(), _refs(), _config()
    )
    assert len(graph.edges) == 1


def test_empty_pyhmmer_search_returns_no_assignments() -> None:
    item = EvalItem(id="e", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0)
    assert PyhmmerSearch().assign((item,)) == []


def test_pyhmmer_golden_recovers_family_member_and_rejects_decoy() -> None:
    search = PyhmmerSearch.from_alignment(_FIXTURES / "family_seed.afa", family_name="FamX")
    detector = FamilyDetector(search=search)
    evals = (
        EvalItem(id="e_member", sequence=_MEMBER, seq_type=SeqType.PROTEIN, label=1.0),
        EvalItem(id="e_decoy", sequence=_DECOY, seq_type=SeqType.PROTEIN, label=0.0),
    )
    refs = (ReferenceItem(id="r_member", sequence=_MEMBER, seq_type=SeqType.PROTEIN),)
    graph = detector.detect(evals, refs, _config(e_value=1e-3))
    contaminated = contaminated_eval_ids(graph)
    assert "e_member" in contaminated
    assert "e_decoy" not in contaminated
