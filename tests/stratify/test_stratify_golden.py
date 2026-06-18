"""(c) Planted silent-failure golden: healthy headline, one bucket that fails.

make_failure_regime() plants accuracy 0.90 overall while the high-identity
(near-train) bucket is 0.00. A correct detector recovers exactly that regime and
flags exactly that bucket -- not the healthy ones.
"""

from __future__ import annotations

from tests.conftest import DEFAULT_SEED
from tests.factories import StratifyRegime, make_failure_regime
from veritas.contracts import MetricName, MetricSpec
from veritas.stratify import (
    StratifiedCurve,
    detect_silent_failures,
    fixed_bins,
    identity_to_nearest_reference,
    performance_curve,
)

_ACCURACY = MetricSpec(name=MetricName.ACCURACY)


def _curve_for_regime() -> tuple[StratifyRegime, StratifiedCurve]:
    regime = make_failure_regime()
    axis = identity_to_nearest_reference(regime.eval_items, regime.graph)
    bins = fixed_bins(regime.n_bins, lo=0.0, hi=1.0)
    curve = performance_curve(
        regime.eval_items, axis, bins, _ACCURACY, seed=DEFAULT_SEED, n_bootstrap=200
    )
    return regime, curve


def test_recovers_the_planted_curve_shape() -> None:
    regime, curve = _curve_for_regime()
    assert curve.aggregate.value == regime.expected_aggregate
    assert {b.index: b.estimate.value for b in curve.buckets} == regime.expected_bucket_values


def test_flags_exactly_the_failing_bucket() -> None:
    regime, curve = _curve_for_regime()
    flags = detect_silent_failures(curve)
    assert tuple(f.bucket_index for f in flags) == regime.expected_flagged_buckets
    (flag,) = flags
    assert flag.bucket_value == 0.0
    assert flag.aggregate_value == 0.9
    assert flag.gap == 0.9  # aggregate - bucket


def test_does_not_flag_the_healthy_buckets() -> None:
    _regime, curve = _curve_for_regime()
    flagged = {f.bucket_index for f in detect_silent_failures(curve)}
    assert flagged.isdisjoint({0, 1, 2})
