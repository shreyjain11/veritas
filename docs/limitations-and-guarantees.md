# Limitations & guarantees

Veritas is built to be trusted in a CI gate, so it states plainly both what it
guarantees and where it is known to be imperfect. The limitations below are
**measured by the test suite**, not estimated.

## Guarantees

### Model-agnostic by construction
Veritas consumes predictions, never the model. There is no way for a model
detail to leak into the audit because the model is not in the loop.

### Provenance on every number
Every reported number is a traced value carrying a `provenance_ref`. The whole
report — metrics, leakage summary, stratification, and disclosed limitations —
is covered by a single `audit_hash` over its canonical JSON. Reading provenance
from a tampered report fails rather than returning a stale hash.

### Determinism
On the pinned platform (the CI image, Python 3.12), audits are **byte-identical**
across runs: fixed seeds, canonical float serialization, and image metadata
stripped from rendered SVGs. There is **no cross-architecture guarantee** —
floating-point and binary-version differences across platforms can change low
bits.

### Honest uncertainty
Every metric is reported with a bootstrap confidence interval, and the
applicable methodological limitations travel inside the report (and are hashed
into it).

### Binary provenance
Each detector resolves its binary once at init and records the **resolved
absolute path** in provenance, so a report names exactly which executable
produced it.

## Limitations (measured)

### Bootstrap CIs under-cover at small n
Confidence intervals use the **percentile bootstrap**, which mildly under-covers
at small sample sizes: empirically about **0.927** coverage at **n=25** for a
nominal 95% interval, rising toward nominal as n grows. Treat intervals on small
buckets or small evaluation sets as optimistic. BCa intervals are not
implemented.

### MinHash prefilter recall is non-conservative
When the MinHash/LSH candidate prefilter is enabled, recall follows an S-curve
rather than a hard cutoff — about **56%** at the nominal Jaccard threshold — and
scattered substitutions can drop a true near-duplicate below candidacy. The
prefilter is recall-oriented, not a guarantee; **disable it for an exhaustive
comparison.**

### Scope
Family (HMMER) and structural (Foldseek) detectors are **protein-only**, and
structural detection requires user-provided structures. Sequence-identity
detection applies to protein and nucleotide sequences.

### Structural detection is fold-level, not interface-level
The structural detector reports a **fold-level** TM-score (Foldseek monomer
TMalign, `max(qtmscore, ttmscore)`). This is a related but **more permissive**
signal than **interface-level** redundancy (e.g. iDist / iAlign): two complexes can
share a fold while their binding interfaces differ. The PPI demonstration's
structural rates are therefore reported as their own quantity and are **not directly
comparable** to interface-redundancy baselines — see [Validation](validation.md).

### Nucleotide sequence search is memory-intensive
MMseqs2 nucleotide search reserves a large k-mer index and can exceed available RAM
on memory-limited machines (e.g. ~7 GB CI runners), aborting with "Cannot fit
databases into NG" even on small inputs. The binary nucleotide differential tests
skip on such runners; the hermetic argv tests still guard the invocation flags
(`--search-type 3`), so a regression in *how* the search is called cannot pass
unnoticed.

## Validation
The demonstration / external-reproduction suite is **complete**: four
demonstrations report real, locked numbers on pinned data — see
[Validation](validation.md). No numbers on these pages are fabricated.

## Future work
Known edges, recorded honestly so they are not silently dropped:

- **Interface-level structural detection.** Add a true interface-level mode
  (interface alignment, e.g. iAlign-style, or Foldseek multimer) so PPI structural
  leakage can be compared *numerically* to interface-redundancy baselines rather
  than corroborated qualitatively against the current fold-level signal.
- **BCa bootstrap intervals.** Confidence intervals use the percentile bootstrap,
  which under-covers at small n (≈0.927 at n=25; see above). Bias-corrected-and-
  accelerated (BCa) intervals would improve small-n coverage; not yet implemented.
- **Lower-memory nucleotide search.** Provide a reduced-memory path (or a documented
  minimum-RAM requirement) so nucleotide search runs on small CI runners without the
  binary tests having to skip.
