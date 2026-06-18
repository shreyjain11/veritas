"""Specificity twin (req A): contamination uncorrelated with correctness ⇒ no gap."""

from __future__ import annotations

import pytest

from tests.factories import make_specificity_control
from veritas.contracts import DeLeakPolicy, MetricName, MetricSpec, ResultStatus
from veritas.metrics import compute_honest

_SPEC = MetricSpec(name=MetricName.ACCURACY, threshold=0.5)


def test_uncorrelated_contamination_does_not_invent_a_gap() -> None:
    case = make_specificity_control()
    result = compute_honest(
        case.eval_items,
        case.graph,
        _SPEC,
        policy=DeLeakPolicy.DROP,
        bootstrap_n=400,
        ci_level=0.95,
        seed=1729,
    )
    assert result.status is ResultStatus.OK
    assert result.reported.value == pytest.approx(case.expected_reported)  # 0.5
    assert result.honest.value == pytest.approx(case.expected_honest)  # 0.5
    assert result.delta.value == pytest.approx(0.0)


def test_delta_confidence_interval_contains_zero() -> None:
    case = make_specificity_control()
    result = compute_honest(
        case.eval_items,
        case.graph,
        _SPEC,
        policy=DeLeakPolicy.DROP,
        bootstrap_n=400,
        ci_level=0.95,
        seed=1729,
    )
    assert result.delta.ci_low is not None and result.delta.ci_high is not None
    assert result.delta.ci_low <= 0.0 <= result.delta.ci_high
