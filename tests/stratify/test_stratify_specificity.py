"""(d) Specificity twin (req A): flat performance ⇒ no false silent-failure flag.

make_failure_specificity_control() makes accuracy 0.75 in EVERY difficulty bucket
(equal to the aggregate). Difficulty varies but performance does not, so a correct
detector must not invent a silent failure.
"""

from __future__ import annotations

from tests.conftest import DEFAULT_SEED
from tests.factories import StratifyRegime, make_failure_specificity_control
from veritas.contracts import MetricName, MetricSpec
from veritas.stratify import (
    StratifiedCurve,
    detect_silent_failures,
    fixed_bins,
    identity_to_nearest_reference,
    performance_curve,
)


def _curve() -> tuple[StratifyRegime, StratifiedCurve]:
    regime = make_failure_specificity_control()
    axis = identity_to_nearest_reference(regime.eval_items, regime.graph)
    bins = fixed_bins(regime.n_bins, lo=0.0, hi=1.0)
    curve = performance_curve(
        regime.eval_items,
        axis,
        bins,
        MetricSpec(name=MetricName.ACCURACY),
        seed=DEFAULT_SEED,
        n_bootstrap=200,
    )
    return regime, curve


def test_flat_performance_is_recovered_as_flat() -> None:
    regime, curve = _curve()
    assert {b.index: b.estimate.value for b in curve.buckets} == regime.expected_bucket_values
    assert curve.aggregate.value == regime.expected_aggregate


def test_flat_performance_raises_no_silent_failure_flag() -> None:
    _regime, curve = _curve()
    assert detect_silent_failures(curve) == ()
