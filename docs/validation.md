# Validation

Veritas separates two kinds of evidence, and reports them differently.

## What is validated now

The **engine and interfaces** are complete and validated by the test suite:

- Contracts, detectors, de-leaking, honest re-scoring, bootstrap CIs,
  stratification, and report assembly are covered by unit, property, and
  integration tests (the suite gates on ≥90% coverage; the project is at 100%).
- **Determinism** is asserted: reports are byte-identical on the pinned platform,
  and the `audit_hash` covers the full report.
- **Provenance** is asserted end-to-end, including the resolved detector binary
  path.
- Methodological limitations are **measured**, not assumed — the bootstrap
  coverage and prefilter-recall numbers on the
  [Limitations](limitations-and-guarantees.md) page come from tests in the suite.

## Reproduction R3 — OverfitNN homology inflation (real results)

This is the reported-vs-honest reproduction: it demonstrates Veritas catching and
quantifying the performance a model gains purely from train/test homology.

We do **not** reproduce a published headline number. Instead we **construct the
maximally-overfit memorizer** that hashFrag
([bioRxiv 2025.01.22.634321](https://www.biorxiv.org/content/10.1101/2025.01.22.634321v2))
describes — predict each test sequence's activity from the label of its single most
sequence-similar training sequence — and show Veritas recovers the inflation that
memorizer's reliance on homology predicts.

!!! note "OverfitNN is a deliberately terrible memorizer"
    OverfitNN is a deliberately terrible memorizer; the point is not that it looks
    good, but that Veritas attributes its signal to leakage.

**Dataset.** Gosai et al. 2024 human lentiMPRA (de Boer lab), K562 activity
(`log2FC`), 200 bp genomic sequences with a chromosome column. **Fetch-only** (the
GAME Zenodo record [14757152](https://zenodo.org/records/14757152) states CC-BY-4.0
while the upstream preprint mentions CC-BY-NC; we never host the bytes — the repo
carries only a pinned manifest and the user fetches from Zenodo). Surrogate model =
OverfitNN; reference set = the declared train split; metric = Spearman; deterministic
(seed 1729, 20,000 train / 5,000 test; nucleotide mmseqs2 de-leak at 0.80 identity).

| split | reported (full test) | honest (de-leaked) | delta (inflation) | leakage |
|---|---|---|---|---|
| **random** | 0.165 [0.137, 0.196] | **0.018 [−0.016, 0.050]** | **0.147 [0.107, 0.186]** | 1230/5000 = 24.6% |
| **chr8+chr9 holdout** | 0.074 [0.046, 0.103] | **0.030 [0.002, 0.056]** | **0.044 [0.009, 0.079]** | 828/5000 = 16.6% |

Stratifying each test set by identity-to-nearest-training-sequence shows the
mechanism directly: the apparent performance lives entirely in the high-identity
bucket and is absent in the low-identity bucket.

| split | high-identity bucket [0.75, 1.0) | low-identity bucket [0, 0.25) |
|---|---|---|
| random | Spearman 0.352 (n=1230) | Spearman 0.018 (n=3770, flagged silent-failure) |
| chr8+chr9 holdout | Spearman 0.147 (n=828) | Spearman 0.030 (n=4172) |

**The two narratives.**

- **Random split — complete memorizer collapse.** Under naive splitting the honest
  metric collapses to a **statistical null** (CI includes 0): the de-leaked memorizer
  has no real predictive ability, and **all** of its apparent 0.165 is leakage.
- **chr8+chr9 holdout — residual leakage survives a leakage-aware split.** Even
  holding out whole chromosomes, ~60% of the apparent signal is still leakage
  (honest 0.030 vs reported 0.074); the inflation is smaller (0.044) but real (its
  CI excludes 0). The honest metric is **reduced but not null** here — that is the
  finding, and Veritas quantifies it. Leakage is **larger still under naive
  splitting** (the random row above).

**Reproducibility.** All numbers are deterministic given the pinned Zenodo archive
(sha256), seed, and mmseqs2 version. A reproducibility bug found while locking this
reproduction — `polars.unique()` does not preserve row order, so a seeded subsample
varied run-to-run — was fixed by sorting before sampling; runs are now byte-stable.
The two split-specific assertions (random: full memorizer-null signature; chr8+chr9:
substantial-but-partial reduction) are locked in `tests/e2e/test_external_repro_overfitnn.py`.

## Reproduction R2 — genomic reverse-complement leakage detection (real results)

A leakage-**detection** demo (not a metric reproduction): does Veritas surface the
homology a naive genomic split leaves in?

On hashFrag's example naive split, **Veritas detects that 80.8% (1616/2000) of test
sequences are exact reverse-complements of training sequences** — genuine same-element
homology. mmseqs nucleotide search runs **both strands** by default, so Veritas's
detector (run exhaustively) flags these reverse-complement duplicates that a
forward-only, MinHash-style screen would miss.

hashFrag handles reverse complements **by default** (it generates them when building
its BLAST database; the `--skip-revcomp` flag toggles this). Its example/tutorial
commands **explicitly pass `--skip-revcomp`** — the example input already carries both
orientations as `_Reversed` records — so the **example default** removed **197 (9.85%)**
test sequences, only **165** of which overlap the reverse-complement set, leaving ~1,450
reverse-complement duplicates in the "filtered" split.

!!! note "Not a takedown"
    This is the hashFrag **example** run with its **default** flags, not a claim that
    hashFrag-the-method is broken or its authors erred. Whether other hashFrag
    configurations capture this is not assessed here. The point is the opposite: Veritas
    performs both-strand detection by default and surfaces reverse-complement homology a
    naive split leaves in — why post-hoc auditing catches what split-creation defaults
    can miss.

The data facts (80.8% reverse-complement rate; 197 removed; 165 overlap) are verified
three ways — mmseqs both-strand search, reverse-complement string match, and removed-set
overlap — and locked in `tests/e2e/test_external_repro_genomic.py` (the string-match
facts need no binary; the both-strand detection needs mmseqs + adequate memory). The
assertion is that Veritas detects the reverse-complement leakage (well above a 0.50
floor) and that it **exceeds the example default's 9.85% removal** — not that it matches
any cited number.

## What is still in progress

- **Leakage-rate reproduction (R1)** — Veritas's detected cross-split homology rate vs
  Bushuiev et al.'s published PPI leakage rates. Cited constants are pinned; the run is
  pending.
- **ProteinGym stratification demo** — MSA-depth silent-failure analysis (no
  contamination claim).
- **PPI demo** — family + structural contamination on a declared train/test split.

!!! warning "No fabricated results"
    Only the R2 and R3 numbers above come from real runs. The items under *still in
    progress* report no numbers until their runs land — the absence is deliberate.
