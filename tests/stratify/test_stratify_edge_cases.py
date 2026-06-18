"""(e) Small / empty / single-class buckets resolve to an explicit ResultStatus.

No bucket ever reports a point estimate it cannot support: empty or below-minimum-N
buckets are INSUFFICIENT_CLEAN_DATA, a single-class bucket under a binary metric is
UNDEFINED_METRIC, value is None (never NaN), and such buckets are never flagged as
silent failures.
"""

from __future__ import annotations

from collections.abc import Sequence

from tests.conftest import DEFAULT_SEED
from tests.factories import make_failure_regime
from veritas.contracts import (
    ContaminationEdge,
    ContaminationGraph,
    DetectorKind,
    EvalItem,
    MetricName,
    MetricSpec,
    ResultStatus,
    SeqType,
)
from veritas.stratify import (
    StratifiedCurve,
    detect_silent_failures,
    fixed_bins,
    identity_to_nearest_reference,
    performance_curve,
)

_BINS = fixed_bins(4, lo=0.0, hi=1.0)
_ACCURACY = MetricSpec(name=MetricName.ACCURACY)


def _item(item_id: str, label: float, prediction: float) -> EvalItem:
    return EvalItem(
        id=item_id, sequence="MKV", seq_type=SeqType.PROTEIN, label=label, prediction=prediction
    )


def _edge(eval_id: str, score: float) -> ContaminationEdge:
    return ContaminationEdge(
        eval_id=eval_id, ref_id="r", score=score, kind=DetectorKind.SEQUENCE, detector_id="d"
    )


def _curve(
    items: Sequence[EvalItem],
    edges: Sequence[ContaminationEdge],
    spec: MetricSpec = _ACCURACY,
    *,
    min_bucket_n: int = 2,
) -> StratifiedCurve:
    graph = ContaminationGraph(edges=tuple(edges))
    axis = identity_to_nearest_reference(items, graph)
    return performance_curve(
        items, axis, _BINS, spec, seed=DEFAULT_SEED, n_bootstrap=100, min_bucket_n=min_bucket_n
    )


def test_empty_bucket_is_insufficient_not_nan() -> None:
    # Items only in buckets 0 and 3; buckets 1 and 2 receive nothing.
    items = tuple(_item(f"a{i}", 1.0, 0.9) for i in range(6)) + tuple(
        _item(f"d{i}", 1.0, 0.9) for i in range(6)
    )
    edges = [_edge(f"d{i}", 0.9) for i in range(6)]
    curve = _curve(items, edges)
    for empty_index in (1, 2):
        bucket = curve.buckets[empty_index]
        assert bucket.n == 0
        assert bucket.estimate.value is None
        assert bucket.estimate.status is ResultStatus.INSUFFICIENT_CLEAN_DATA


def test_below_minimum_n_bucket_is_insufficient() -> None:
    items = (*(_item(f"a{i}", 1.0, 0.9) for i in range(5)), _item("b0", 1.0, 0.9))
    edges = [_edge("b0", 0.3)]  # a single item lands in bucket 1
    curve = _curve(items, edges, min_bucket_n=2)
    assert curve.buckets[1].n == 1
    assert curve.buckets[1].estimate.value is None
    assert curve.buckets[1].estimate.status is ResultStatus.INSUFFICIENT_CLEAN_DATA


def test_single_class_bucket_is_undefined_for_a_binary_metric() -> None:
    # bucket 0 has both classes (AUROC defined); bucket 3 is single-class (undefined).
    items = (
        _item("a0", 0.0, 0.1),
        _item("a1", 0.0, 0.2),
        _item("a2", 1.0, 0.8),
        _item("a3", 1.0, 0.9),
        _item("d0", 1.0, 0.5),
        _item("d1", 1.0, 0.6),
        _item("d2", 1.0, 0.7),
    )
    edges = [_edge("d0", 0.9), _edge("d1", 0.9), _edge("d2", 0.9)]
    curve = _curve(items, edges, MetricSpec(name=MetricName.AUROC))
    assert curve.buckets[0].estimate.status is ResultStatus.OK
    assert curve.buckets[3].estimate.value is None
    assert curve.buckets[3].estimate.status is ResultStatus.UNDEFINED_METRIC


def test_non_ok_buckets_are_never_flagged() -> None:
    # A healthy aggregate plus an insufficient bucket: the insufficient bucket must
    # not be flagged (and detection must not crash on its None value).
    items = (*(_item(f"a{i}", 1.0, 0.9) for i in range(10)), _item("b0", 1.0, 0.1))
    edges = [_edge("b0", 0.3)]  # lone wrong item in bucket 1, below min N
    curve = _curve(items, edges, min_bucket_n=2)
    flagged = {f.bucket_index for f in detect_silent_failures(curve)}
    assert 1 not in flagged


def test_undefined_aggregate_yields_no_flags() -> None:
    # AUROC on all-single-class data: the aggregate itself is undefined, so silent-
    # failure detection has no healthy baseline to compare against and flags nothing.
    items = tuple(_item(f"a{i}", 1.0, 0.9) for i in range(6))
    curve = _curve(items, [], MetricSpec(name=MetricName.AUROC))
    assert curve.aggregate.status is ResultStatus.UNDEFINED_METRIC
    assert detect_silent_failures(curve) == ()


def test_lower_is_better_flags_the_high_buckets() -> None:
    # With greater_is_better=False, "worse" means HIGHER. On the failure regime
    # (aggregate 0.90), the all-correct buckets (1.0) are now the silent failures
    # and the all-wrong bucket (0.0) is not. min_gap=0.05 keeps us off the float
    # boundary (1.0 - 0.9 == 0.0999...) -- the point here is the direction, not the cutoff.
    regime = make_failure_regime()
    curve = _curve(
        regime.eval_items,
        regime.graph.edges,
        MetricSpec(name=MetricName.ACCURACY, greater_is_better=False),
    )
    flagged = {f.bucket_index for f in detect_silent_failures(curve, min_gap=0.05)}
    assert flagged == {0, 1, 2}
