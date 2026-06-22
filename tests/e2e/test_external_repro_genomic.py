"""(e) External reproduction R2 -- genomic cross-split homology (hashFrag).

Target: bioRxiv 2025.01.22.634321, "Characterizing homology-induced data leakage and
memorization in genome-trained sequence models" (hashFrag).

REFRAME (verified against the released data, 2026-06): hashFrag's example data is
SEQUENCES ONLY (no expression labels), so we cannot compute a model metric delta from it.
What it DOES provide is a declared train/test split plus hashFrag's own homology-pruned
("filtered") test set. So R2 is a LEAKAGE-RATE reproduction: "cross-split homology against
the declared train/test split." Veritas's nucleotide sequence detector should flag the
same fraction of test sequences as homologous to train that hashFrag removed to build the
filtered set. No "model-training leakage" claim (the example data is splits, not a model).

The metric-DELTA version (the OverfitNN memorizer the plan described) needs labels; that is
deferred to a labeled MPRA dataset, or to the LOCO-EPI backup (demos/loco_epi), which has
labels + a model (AUROC ~0.90 random-split -> ~0.50 LOCO; arXiv:2504.00306 Tables 4 & 5).
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.external, pytest.mark.requires_mmseqs]

# Computed from the released hashFrag example slice (NOT a paper headline; verifiable):
#   de-Boer-Lab/hashFrag, data/ @ commit c92324f33f6e19266884d32b693ae907d5eb2dbf
#   example_test_split.fa = 2000 sequences; example_test_split.filtered.fa = 1803 kept
#   -> 197 removed as homologous to example_train_split.fa (8000) at hashFrag's default
#      BLAST threshold. Vendored + pinned in demos/regulatory_dna_hashfrag/manifest.toml.
_HASHFRAG_TEST_TOTAL = 2000
_HASHFRAG_TEST_KEPT = 1803
_HASHFRAG_REMOVAL_RATE = (
    _HASHFRAG_TEST_TOTAL - _HASHFRAG_TEST_KEPT
) / _HASHFRAG_TEST_TOTAL  # 0.0985

_PUBLISHED_LEAKAGE_RATE = _HASHFRAG_REMOVAL_RATE
_TOLERANCE = 0.03  # absolute leakage-rate tolerance

# The hashFrag slice IS vendored in-repo, but the full-tier run is pending explicit
# approval (don't run audits yet). Collected for constant verification; does not run.
_RUN_PENDING_APPROVAL = True


def test_reproduces_hashfrag_cross_split_homology_rate() -> None:
    if _RUN_PENDING_APPROVAL:
        pytest.skip(
            "R2 constants pinned; full-tier run pending approval (demos/regulatory_dna_hashfrag)"
        )
    # When enabled: eval = example_test_split.fa, reference = example_train_split.fa
    # (sequences only; placeholder labels, unused by detection), run the mmseqs nucleotide
    # detector at a threshold matched to hashFrag, and assert
    #   abs(detected_contaminated_fraction - _PUBLISHED_LEAKAGE_RATE) <= _TOLERANCE
