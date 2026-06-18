"""Reported-vs-honest golden: the planted inflation gap is recovered exactly."""

from __future__ import annotations

import pytest

from tests.factories import make_inflation_construction, make_partial_contamination
from veritas.contracts import DeLeakPolicy, MetricName, MetricSpec, ResultStatus
from veritas.metrics import compute_honest

_SPEC = MetricSpec(name=MetricName.ACCURACY, threshold=0.5)


def test_honest_recovers_planted_reported_and_honest_and_delta() -> None:
    case = make_inflation_construction()
    result = compute_honest(
        case.eval_items,
        case.graph,
        _SPEC,
        policy=DeLeakPolicy.DROP,
        bootstrap_n=200,
        ci_level=0.95,
        seed=1729,
    )
    assert result.status is ResultStatus.OK
    assert result.reported.value == pytest.approx(case.expected_reported)  # 0.8
    assert result.honest.value == pytest.approx(case.expected_honest)  # 0.6
    assert result.delta.value == pytest.approx(case.expected_delta)  # 0.2
    assert result.n_eval == 20
    assert result.n_contaminated == 10
    assert result.n_clean == 10


def test_honest_is_not_greater_than_reported_under_inflation() -> None:
    case = make_inflation_construction()
    result = compute_honest(
        case.eval_items,
        case.graph,
        _SPEC,
        policy=DeLeakPolicy.DROP,
        bootstrap_n=200,
        ci_level=0.95,
        seed=1729,
    )
    assert result.honest.value is not None and result.reported.value is not None
    assert result.honest.value <= result.reported.value


def test_each_estimate_carries_a_confidence_interval() -> None:
    case = make_inflation_construction()
    result = compute_honest(
        case.eval_items,
        case.graph,
        _SPEC,
        policy=DeLeakPolicy.DROP,
        bootstrap_n=200,
        ci_level=0.95,
        seed=1729,
    )
    for estimate in (result.reported, result.honest):
        assert estimate.value is not None
        assert estimate.ci_low is not None and estimate.ci_high is not None
        assert estimate.ci_low <= estimate.value <= estimate.ci_high


def test_reweight_differs_from_drop_on_partial_contamination() -> None:
    # Fractional reweight keeps a borderline item at partial weight, so the honest
    # metric is genuinely different from dropping all contaminated items.
    case = make_partial_contamination()
    dropped = compute_honest(
        case.eval_items,
        case.graph,
        _SPEC,
        policy=DeLeakPolicy.DROP,
        bootstrap_n=200,
        ci_level=0.95,
        seed=1729,
    )
    reweighted = compute_honest(
        case.eval_items,
        case.graph,
        _SPEC,
        policy=DeLeakPolicy.REWEIGHT,
        bootstrap_n=200,
        ci_level=0.95,
        seed=1729,
    )
    assert dropped.honest.value == pytest.approx(case.expected_drop_honest)  # 0.5
    assert reweighted.honest.value == pytest.approx(case.expected_reweight_honest)  # 1.3/2.3
    assert dropped.honest.value is not None and reweighted.honest.value is not None
    assert abs(reweighted.honest.value - dropped.honest.value) > 1e-3
