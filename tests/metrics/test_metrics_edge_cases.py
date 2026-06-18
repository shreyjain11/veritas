"""Edge cases (req B): undefined metrics raise; ties/degenerate handled deterministically."""

from __future__ import annotations

import numpy as np
import pytest

from veritas.contracts import MetricName
from veritas.metrics import UndefinedMetricError, compute_metric


def test_auroc_single_class_labels_is_undefined() -> None:
    with pytest.raises(UndefinedMetricError):
        compute_metric(MetricName.AUROC, np.array([1.0, 1.0, 1.0]), np.array([0.1, 0.5, 0.9]))


def test_auprc_no_positives_is_undefined() -> None:
    with pytest.raises(UndefinedMetricError):
        compute_metric(MetricName.AUPRC, np.array([0.0, 0.0, 0.0]), np.array([0.1, 0.5, 0.9]))


def test_spearman_constant_input_is_undefined() -> None:
    with pytest.raises(UndefinedMetricError):
        compute_metric(MetricName.SPEARMAN, np.array([1.0, 2.0, 3.0]), np.array([5.0, 5.0, 5.0]))


def test_pearson_constant_input_is_undefined() -> None:
    with pytest.raises(UndefinedMetricError):
        compute_metric(MetricName.PEARSON, np.array([1.0, 2.0, 3.0]), np.array([5.0, 5.0, 5.0]))


def test_auroc_with_score_ties_is_deterministic() -> None:
    labels = np.array([0.0, 1.0, 1.0, 0.0])
    scores = np.array([0.5, 0.5, 0.9, 0.1])  # a tie between a positive and a negative
    first = compute_metric(MetricName.AUROC, labels, scores)
    second = compute_metric(MetricName.AUROC, labels, scores)
    assert first == second


def test_mcc_degenerate_prediction_returns_zero() -> None:
    # All predictions one class -> MCC denominator is 0; defined as 0.0 (matches sklearn).
    labels = np.array([0.0, 1.0, 0.0, 1.0])
    scores = np.array([0.9, 0.9, 0.9, 0.9])  # all predicted positive
    assert compute_metric(MetricName.MCC, labels, scores, threshold=0.5) == pytest.approx(0.0)


def test_f1_no_predicted_or_actual_positives_returns_zero() -> None:
    labels = np.array([0.0, 0.0])
    scores = np.array([0.1, 0.2])  # none predicted positive
    assert compute_metric(MetricName.F1, labels, scores, threshold=0.5) == pytest.approx(0.0)


@pytest.mark.parametrize("name", [MetricName.SPEARMAN, MetricName.PEARSON])
def test_correlation_metrics_reject_fractional_weights(name: MetricName) -> None:
    # Fractional weights have no standard definition for rank/correlation metrics;
    # reweight must raise rather than silently fall back (binary weights == subset are OK).
    labels = np.array([1.0, 2.0, 3.0, 4.0])
    scores = np.array([1.0, 2.0, 3.0, 4.0])
    fractional = np.array([1.0, 0.5, 1.0, 1.0])
    with pytest.raises(UndefinedMetricError):
        compute_metric(name, labels, scores, weights=fractional)
