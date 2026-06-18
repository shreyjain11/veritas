"""(b) Performance-vs-difficulty curve API.

A StratifiedCurve carries, per difficulty bucket, an n and a MetricEstimate
(value + status + bootstrap CI, reusing the Phase-3 bootstrap), plus an aggregate
estimate over all items. Bucket edges come from a Bins object on a difficulty axis.
"""

from __future__ import annotations

import pytest

from tests.conftest import DEFAULT_SEED
from tests.factories import make_failure_regime
from veritas.contracts import (
    EvalItem,
    MetricName,
    MetricSpec,
    ResultStatus,
    SeqType,
)
from veritas.stratify import (
    BucketResult,
    StratifiedCurve,
    fixed_bins,
    identity_to_nearest_reference,
    performance_curve,
)

_ACCURACY = MetricSpec(name=MetricName.ACCURACY)


def _curve() -> StratifiedCurve:
    regime = make_failure_regime()
    axis = identity_to_nearest_reference(regime.eval_items, regime.graph)
    bins = fixed_bins(regime.n_bins, lo=0.0, hi=1.0)
    return performance_curve(
        regime.eval_items,
        axis,
        bins,
        _ACCURACY,
        seed=DEFAULT_SEED,
        n_bootstrap=200,
    )


def test_curve_has_one_bucket_per_bin_in_axis_order() -> None:
    curve = _curve()
    assert isinstance(curve, StratifiedCurve)
    assert curve.metric is MetricName.ACCURACY
    assert len(curve.buckets) == 4
    assert [b.index for b in curve.buckets] == [0, 1, 2, 3]
    # buckets carry their axis range edges
    assert (curve.buckets[0].lo, curve.buckets[0].hi) == (0.0, 0.25)
    assert (curve.buckets[3].lo, curve.buckets[3].hi) == (0.75, 1.0)


def test_bucket_results_carry_n_and_metric_estimate() -> None:
    curve = _curve()
    assert all(isinstance(b, BucketResult) for b in curve.buckets)
    assert [b.n for b in curve.buckets] == [15, 15, 15, 5]
    for bucket in curve.buckets:
        assert bucket.estimate.status is ResultStatus.OK
        assert bucket.estimate.value is not None
        assert bucket.estimate.ci_low is not None and bucket.estimate.ci_high is not None


def test_bucket_values_match_planted_accuracy() -> None:
    curve = _curve()
    values = {b.index: b.estimate.value for b in curve.buckets}
    assert values == {0: 1.0, 1: 1.0, 2: 1.0, 3: 0.0}


def test_aggregate_is_over_all_items() -> None:
    curve = _curve()
    assert curve.aggregate.value == 0.9  # 45/50
    assert curve.aggregate.status is ResultStatus.OK


def test_curve_is_deterministic_given_seed() -> None:
    assert _curve() == _curve()


def test_missing_prediction_is_rejected() -> None:
    items = (
        EvalItem(id="x", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0),
    )  # no prediction
    with pytest.raises(ValueError, match="prediction"):
        performance_curve(
            items,
            {"x": 0.0},
            fixed_bins(2, lo=0.0, hi=1.0),
            _ACCURACY,
            seed=DEFAULT_SEED,
            n_bootstrap=10,
        )


def test_missing_axis_value_is_rejected() -> None:
    # An item present in eval_items but absent from axis_values is a clear error,
    # not a bare KeyError (mirrors the missing-prediction guard).
    items = (EvalItem(id="x", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.9),)
    with pytest.raises(ValueError, match="axis_values"):
        performance_curve(
            items,
            {},  # no axis value for "x"
            fixed_bins(2, lo=0.0, hi=1.0),
            _ACCURACY,
            seed=DEFAULT_SEED,
            n_bootstrap=10,
        )
