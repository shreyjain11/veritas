"""MinHash/LSH candidate prefilter (datasketch).

A recall-oriented, scale-only optimization: it returns candidate (eval, ref)
pairs whose k-mer Jaccard is high. Because k-mer Jaccard is NOT monotone with
alignment identity, this is NOT conservative w.r.t. a detector's identity
threshold (scattered substitutions destroy shared k-mers while keeping identity
high) — so correctness tests run the detectors with the prefilter disabled. See
tests/contamination/test_prefilter.py::test_prefilter_is_not_conservative_wrt_identity.
"""

from __future__ import annotations

from collections.abc import Sequence

from datasketch import MinHash, MinHashLSH

from veritas.contracts import EvalItem, ReferenceItem

#: k-mer (shingle) size. Pinned: the non-conservativeness test mutates every 5th residue.
DEFAULT_K = 5
#: LSH Jaccard threshold. Recall-oriented (cast a wide net; the aligner filters precisely).
DEFAULT_THRESHOLD = 0.5
DEFAULT_NUM_PERM = 128
_SEED = 1


def _shingles(sequence: str, k: int) -> set[bytes]:
    if len(sequence) <= k:
        return {sequence.encode("ascii")}
    return {sequence[i : i + k].encode("ascii") for i in range(len(sequence) - k + 1)}


def _minhash(sequence: str, k: int, num_perm: int) -> MinHash:
    minhash = MinHash(num_perm=num_perm, seed=_SEED)
    for shingle in _shingles(sequence, k):
        minhash.update(shingle)
    return minhash


def candidate_pairs(
    eval_items: Sequence[EvalItem],
    reference_items: Sequence[ReferenceItem],
    *,
    k: int = DEFAULT_K,
    threshold: float = DEFAULT_THRESHOLD,
    num_perm: int = DEFAULT_NUM_PERM,
) -> set[tuple[str, str]]:
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    for ref in reference_items:
        lsh.insert(ref.id, _minhash(ref.sequence, k, num_perm))

    pairs: set[tuple[str, str]] = set()
    for item in eval_items:
        for ref_id in lsh.query(_minhash(item.sequence, k, num_perm)):
            pairs.add((item.id, str(ref_id)))
    return pairs
