"""(e) External reproduction R1 -- protein-interaction homology leakage (Bushuiev et al.).

Target: arXiv:2404.10457, "Revealing data leakage in protein interaction benchmarks".

REFRAME (verified against the paper, 2026-06): this paper releases NO trained model and
reports data-leakage RATES (via iDist), not model-performance deltas. So R1 is a
LEAKAGE-RATE reproduction: "cross-split homology against the benchmark's own declared
train/test split." Veritas's detected contaminated fraction (sequence detector at the
same identity threshold) should match the paper's reported leakage rate within tolerance.
We make NO "model-training leakage" claim here -- no model was released or trained on the
split, so the only honest claim is benchmark cross-split homology.

Published leakage rates (iDist; fraction of test PPIs leaked from train), quoted with
source locations -- read from the paper full text, never invented:
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.external, pytest.mark.requires_mmseqs]

# arXiv:2404.10457 (v1/v2), all on the SKEMPI/DIPS/PDB PPI benchmarks:
#   §3.2 & Fig 1  -- MMseqs2 sequence-similarity split @ 30% identity: "a leakage rate of 30%"
_BUSHUIEV_LEAKAGE_RATE_MMSEQS30 = 0.30
#   §3.1 & Fig 1  -- PPI-code-based splits: "on average, lead to 86% data leakage"
_BUSHUIEV_LEAKAGE_RATE_PPI_CODE = 0.86
#   §4.2 (also §3.1: "56% (57%, 57%, and 54%)") -- SKEMPI v2.0 PPI-code split: 56% leaked,
#   vs a domain-expertise split: 0%.
_BUSHUIEV_LEAKAGE_RATE_SKEMPI_PPI_CODE = 0.56

# Primary reproduction target: the MMseqs2 30%-identity split, because Veritas's sequence
# detector at identity_threshold=0.30 is the directly comparable method.
_PUBLISHED_LEAKAGE_RATE = _BUSHUIEV_LEAKAGE_RATE_MMSEQS30
_TOLERANCE = 0.05  # absolute leakage-rate tolerance (pass = |veritas_rate - published| <= tol)

# Data is fetch-only (PPIRef is MIT but the underlying SKEMPI/DIPS/PDB data carry their own
# academic terms -- see demos/ppi_bushuiev/manifest.toml) AND the full-tier run is pending
# explicit approval. The test is collected (constants verifiable) but does not run yet.
_RUN_PENDING_APPROVAL = True


def test_reproduces_bushuiev_ppi_cross_split_homology_rate() -> None:
    if _RUN_PENDING_APPROVAL:
        pytest.skip("R1 constants pinned; full-tier run pending approval (see demos/ppi_bushuiev)")
    # When enabled: load the SKEMPI/DIPS benchmark + its declared train split as the
    # reference, run the mmseqs sequence detector at identity 0.30, and assert
    #   abs(report.leakage.fraction_contaminated - _PUBLISHED_LEAKAGE_RATE) <= _TOLERANCE
