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

## Validation in progress
The demonstration suite and external reproductions are not yet reported — see
[Validation](validation.md). No demonstration or reproduction numbers appear in
these docs until the benchmarks are finalized.
