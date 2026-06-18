# Detectors

A detector finds edges between evaluation items and reference items that
indicate the model could have seen (something equivalent to) the test case
during training. Each detector emits a `ContaminationGraph`; the orchestrator
combines them under the configured `combine_policy`.

## Sequence identity — MMseqs2

The default detector. Flags evaluation/reference pairs above an identity
threshold (with optional coverage / e-value / score thresholds). Suitable for
protein and nucleotide sequences.

```json
{ "kind": "sequence", "name": "mmseqs", "identity_threshold": 0.3 }
```

A MinHash/LSH prefilter narrows the candidate set before exact comparison. It is
recall-oriented, not exhaustive — see [Limitations](limitations-and-guarantees.md).
Disable it for an exhaustive comparison.

## Family — HMMER

Flags pairs that hit the same profile/family even when pairwise identity is low.
Catches remote homology that sequence identity misses. Protein-only.

## Structural — Foldseek

Flags structural near-duplicates using Foldseek (which applies its own
prefilter, so the MinHash prefilter is skipped for this detector). Requires
user-provided structures. Protein-only.

## Combining detectors

`combine_policy` controls how multiple detectors' graphs merge (e.g. union).
`deleak_policy` controls what happens to flagged evaluation items when computing
the honest metric (e.g. `drop`). Both are recorded in provenance.

## Binary resolution

Each backend resolves its binary **once at detector init**, via
`VERITAS_<TOOL>_BIN` if set, otherwise `PATH`. The resolved absolute path is
stored and recorded in the report's provenance so an audit names exactly which
binary produced it.
