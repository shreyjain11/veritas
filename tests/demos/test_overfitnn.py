"""The OverfitNN memorizer is deterministic and label-correct (hermetic; fake search).

Predictions = the nearest training sequence's label; no hit -> mean training label; ties
break on the smallest ref_id. A fake search injects planted hits, so these run with no
mmseqs binary and no real data.
"""

from __future__ import annotations

import pytest

from veritas.contamination.hits import SequenceHit
from veritas.contracts import EvalItem, ReferenceItem, SeqType
from veritas.demos.overfitnn import overfitnn_predictions

_SEQ = "ACGTACGTACGTACGTACGTACGTACGTACGT"
_LABELS = {"r1": 5.0, "r2": -3.0}


class _FakeSearch:
    def __init__(self, hits: list[SequenceHit]) -> None:
        self._hits = list(hits)

    def search(
        self,
        eval_items: tuple[EvalItem, ...],
        reference_items: tuple[ReferenceItem, ...],
        *,
        candidate_pairs: set[tuple[str, str]],
    ) -> list[SequenceHit]:
        return list(self._hits)


def _eval(item_id: str) -> EvalItem:
    return EvalItem(id=item_id, seq_type=SeqType.NUCLEOTIDE, sequence=_SEQ, label=0.0)


def _ref(item_id: str) -> ReferenceItem:
    return ReferenceItem(id=item_id, seq_type=SeqType.NUCLEOTIDE, sequence=_SEQ)


def _hit(eval_id: str, ref_id: str, identity: float) -> SequenceHit:
    return SequenceHit(eval_id=eval_id, ref_id=ref_id, identity=identity, coverage=1.0)


def test_predicts_label_of_the_nearest_training_sequence() -> None:
    evals = (_eval("t1"), _eval("t2"))
    refs = (_ref("r1"), _ref("r2"))
    hits = [_hit("t1", "r1", 0.9), _hit("t1", "r2", 0.4), _hit("t2", "r2", 0.7)]
    preds = overfitnn_predictions(evals, refs, _LABELS, _FakeSearch(hits), use_prefilter=False)
    assert preds == {"t1": 5.0, "t2": -3.0}  # t1->r1 (0.9), t2->r2 (0.7)


def test_falls_back_to_mean_training_label_when_no_hit() -> None:
    preds = overfitnn_predictions(
        (_eval("t3"),), (_ref("r1"), _ref("r2")), _LABELS, _FakeSearch([]), use_prefilter=False
    )
    assert preds["t3"] == pytest.approx(1.0)  # mean(5.0, -3.0)


def test_identity_ties_break_on_smallest_ref_id() -> None:
    hits = [_hit("t1", "r2", 0.8), _hit("t1", "r1", 0.8)]  # equal identity
    preds = overfitnn_predictions(
        (_eval("t1"),), (_ref("r1"), _ref("r2")), _LABELS, _FakeSearch(hits), use_prefilter=False
    )
    assert preds["t1"] == 5.0  # r1 < r2 wins


def test_hit_to_an_unlabeled_reference_falls_back() -> None:
    hits = [_hit("t1", "ghost", 0.95)]  # ghost has no label
    preds = overfitnn_predictions(
        (_eval("t1"),), (_ref("r1"), _ref("r2")), _LABELS, _FakeSearch(hits), use_prefilter=False
    )
    assert preds["t1"] == pytest.approx(1.0)  # falls back to mean


def test_empty_reference_labels_is_rejected() -> None:
    with pytest.raises(ValueError, match="reference label"):
        overfitnn_predictions(
            (_eval("t1"),), (_ref("r1"),), {}, _FakeSearch([]), use_prefilter=False
        )


def test_prefilter_path_is_exercised() -> None:
    # use_prefilter=True runs the MinHash candidate_pairs path; the fake search ignores it.
    preds = overfitnn_predictions(
        (_eval("t1"),), (_ref("r1"), _ref("r2")), _LABELS, _FakeSearch([_hit("t1", "r1", 0.9)])
    )
    assert preds["t1"] == 5.0
