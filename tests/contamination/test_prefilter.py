"""MinHash candidate prefilter: deterministic, recalls near-duplicates, prunes unrelated."""

from __future__ import annotations

from veritas.contamination.prefilter import candidate_pairs
from veritas.contracts import EvalItem, ReferenceItem, SeqType


def _eval(item_id: str, sequence: str) -> EvalItem:
    return EvalItem(id=item_id, sequence=sequence, seq_type=SeqType.PROTEIN, label=1.0)


def _ref(item_id: str, sequence: str) -> ReferenceItem:
    return ReferenceItem(id=item_id, sequence=sequence, seq_type=SeqType.PROTEIN)


_LONG = "MKVLAImkVGGSSTTRPQ" * 4  # long enough for k-mer shingling
_UNRELATED = "WWWWYYYYCCCCHHHHDD" * 4


def test_exact_duplicate_is_a_candidate() -> None:
    pairs = candidate_pairs((_eval("e1", _LONG),), (_ref("r1", _LONG),))
    assert ("e1", "r1") in pairs


def test_unrelated_sequence_is_pruned() -> None:
    pairs = candidate_pairs((_eval("e1", _LONG),), (_ref("r1", _UNRELATED),))
    assert ("e1", "r1") not in pairs


def test_near_duplicate_is_a_candidate() -> None:
    near = _LONG[:-3] + "AAA"  # a few residues changed
    pairs = candidate_pairs((_eval("e1", _LONG),), (_ref("r1", near),))
    assert ("e1", "r1") in pairs


def test_is_deterministic() -> None:
    evals = (_eval("e1", _LONG), _eval("e2", _UNRELATED))
    refs = (_ref("r1", _LONG), _ref("r2", _UNRELATED))
    assert candidate_pairs(evals, refs) == candidate_pairs(evals, refs)


def test_short_sequences_are_shingled_whole() -> None:
    # A sequence no longer than the shingle size becomes a single shingle.
    pairs = candidate_pairs((_eval("e", "ACG"),), (_ref("r", "ACG"),))
    assert ("e", "r") in pairs


def test_prefilter_is_not_conservative_wrt_identity() -> None:
    """The prefilter recalls on k-mer Jaccard, which is NOT monotone with identity.

    Mutating every k-th residue keeps alignment identity high (~80%) while changing
    every aligned k-mer, so shared-k-mer Jaccard collapses and the prefilter drops
    the pair. This is exactly why golden/differential correctness tests run with the
    prefilter disabled — it cannot be trusted to retain everything above the
    detector's identity threshold.
    """
    base = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKA"
    chars = list(base)
    for i in range(0, len(chars), 5):  # default shingle size is 5
        chars[i] = "W" if chars[i] != "W" else "G"
    variant = "".join(chars)  # ~80% identical to base, but ~no shared 5-mers

    pairs = candidate_pairs((_eval("e1", base),), (_ref("r1", variant),))
    assert ("e1", "r1") not in pairs
