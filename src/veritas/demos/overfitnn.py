"""Deterministic OverfitNN surrogate: the memorizer hashFrag describes.

For each evaluation sequence, predict the LABEL of its most sequence-similar TRAINING
sequence (nearest neighbour by identity, via the same mmseqs search path the detector
uses). No training, no randomness -- byte-reproducible given the data, the search
backend/version, and the de-leak threshold. An eval item with no usable hit falls back to
the mean training label; identity ties break on the smallest ref_id.

By construction this memorizer scores well on test sequences homologous to the training
set and poorly once those are removed -- exactly the homology-driven inflation hashFrag
characterizes. The candidate prefilter is recall-oriented, so a missed near-duplicate only
makes the memorizer look WEAKER -- the recovered inflation is therefore conservative.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from veritas.contamination.hits import SequenceHit
from veritas.contamination.prefilter import candidate_pairs
from veritas.contamination.sequence_identity import SequenceSearch
from veritas.contracts import EvalItem, ReferenceItem


def overfitnn_predictions(
    eval_items: Sequence[EvalItem],
    reference_items: Sequence[ReferenceItem],
    reference_labels: Mapping[str, float],
    search: SequenceSearch,
    *,
    use_prefilter: bool = True,
) -> dict[str, float]:
    """Predict each eval id's label from its nearest training sequence (see module docs)."""
    if not reference_labels:
        raise ValueError("overfitnn_predictions requires at least one reference label")
    evals = tuple(eval_items)
    refs = tuple(reference_items)
    candidates = (
        candidate_pairs(evals, refs)
        if use_prefilter
        else {(e.id, r.id) for e in evals for r in refs}
    )

    best: dict[str, SequenceHit] = {}
    for hit in search.search(evals, refs, candidate_pairs=candidates):
        current = best.get(hit.eval_id)
        if (
            current is None
            or hit.identity > current.identity
            or (hit.identity == current.identity and hit.ref_id < current.ref_id)
        ):
            best[hit.eval_id] = hit

    fallback = sum(reference_labels.values()) / len(reference_labels)
    predictions: dict[str, float] = {}
    for item in evals:
        nearest = best.get(item.id)
        predictions[item.id] = (
            reference_labels[nearest.ref_id]
            if nearest is not None and nearest.ref_id in reference_labels
            else fallback
        )
    return predictions
