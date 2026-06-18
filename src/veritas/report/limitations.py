"""Known methodological limitations, disclosed in the report (and hashed into it).

``collect_limitations`` runs during report assembly; the bootstrap caveat is
always disclosed (every CI is a percentile bootstrap), the MinHash caveat only
when the prefilter was enabled (otherwise it is irrelevant).
"""

from __future__ import annotations

from veritas.contracts import Limitation

BOOTSTRAP_SMALL_N = Limitation(
    id="bootstrap_small_n",
    title="Bootstrap confidence intervals under-cover at small n",
    detail=(
        "Confidence intervals use the percentile bootstrap, which mildly under-covers at "
        "small sample sizes: empirically about 0.927 coverage at n=25 for a nominal 95% "
        "interval, rising toward nominal as n grows. Treat intervals on small buckets or "
        "sets as optimistic."
    ),
)

MINHASH_NONCONSERVATIVE = Limitation(
    id="minhash_nonconservative",
    title="MinHash prefilter recall is non-conservative",
    detail=(
        "When the MinHash/LSH candidate prefilter is enabled, recall follows an S-curve "
        "rather than a hard cutoff (about 56% at the nominal Jaccard threshold), and "
        "scattered substitutions can drop a true near-duplicate below candidacy. The "
        "prefilter is recall-oriented, not a guarantee; disable it for an exhaustive "
        "comparison."
    ),
)


def collect_limitations(*, prefilter_enabled: bool) -> tuple[Limitation, ...]:
    """The limitations applicable to an audit, given its configuration."""
    limitations = [BOOTSTRAP_SMALL_N]
    if prefilter_enabled:
        limitations.append(MINHASH_NONCONSERVATIVE)
    return tuple(limitations)
