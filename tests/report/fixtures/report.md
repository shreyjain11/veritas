# Veritas Audit Report - demo-benchmark

- **audit_hash:** `a2c8575bcfe5bed840e7304799f38d485746a32bcd744062fa5a473a4f38fc35`
- **status:** ok

## Metrics

| metric | value | 95% CI | provenance |
| --- | --- | --- | --- |
| Reported | 0.875 | [0.5, 0.95] | `prov:reported` |
| Honest | 0.625 | [0.5, 0.95] | `prov:honest` |
| Delta | 0.25 | [0.5, 0.95] | `prov:delta` |

## Leakage

- eval items: 50
- contaminated: 5 (fraction 0.1)
- detector mmseqs: 5

## Provenance

- seed: 1729
- mmseqs pinned: 18.8cc5c
- mmseqs runtime: 18.8cc5c

## Limitations

### Bootstrap confidence intervals under-cover at small n

Confidence intervals use the percentile bootstrap, which mildly under-covers at small sample sizes: empirically about 0.927 coverage at n=25 for a nominal 95% interval, rising toward nominal as n grows. Treat intervals on small buckets or sets as optimistic.

### MinHash prefilter recall is non-conservative

When the MinHash/LSH candidate prefilter is enabled, recall follows an S-curve rather than a hard cutoff (about 56% at the nominal Jaccard threshold), and scattered substitutions can drop a true near-duplicate below candidacy. The prefilter is recall-oriented, not a guarantee; disable it for an exhaustive comparison.

