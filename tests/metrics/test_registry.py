"""Metric registry: task-type guard and full enum coverage."""

from __future__ import annotations

import numpy as np
import pytest

from veritas.contracts import MetricName
from veritas.metrics import compute_metric, requires_binary_labels

_BINARY_LABEL_METRICS = {
    MetricName.AUROC,
    MetricName.AUPRC,
    MetricName.ACCURACY,
    MetricName.MCC,
    MetricName.F1,
}
_CONTINUOUS_METRICS = {MetricName.SPEARMAN, MetricName.PEARSON}


@pytest.mark.parametrize("name", sorted(_BINARY_LABEL_METRICS))
def test_binary_label_metrics_require_binary_labels(name: MetricName) -> None:
    assert requires_binary_labels(name) is True


@pytest.mark.parametrize("name", sorted(_CONTINUOUS_METRICS))
def test_continuous_metrics_do_not_require_binary_labels(name: MetricName) -> None:
    assert requires_binary_labels(name) is False


def test_binary_metric_rejects_non_binary_labels() -> None:
    labels = np.array([0.0, 1.0, 2.0])  # 2.0 is not a binary label
    scores = np.array([0.1, 0.5, 0.9])
    with pytest.raises(ValueError):
        compute_metric(MetricName.AUROC, labels, scores)


def test_every_metric_name_is_supported() -> None:
    # A representative defined input for each metric; no MetricName goes unhandled.
    labels = np.array([0.0, 1.0, 0.0, 1.0])
    scores = np.array([0.2, 0.8, 0.3, 0.9])
    for name in MetricName:
        assert isinstance(compute_metric(name, labels, scores), float)


def test_correlation_metric_with_binary_weights_uses_subset() -> None:
    labels = np.array([1.0, 2.0, 3.0, 4.0])
    scores = np.array([1.0, 2.0, 3.0, 4.0])
    weights = np.array([0.0, 1.0, 1.0, 1.0])  # binary -> drop item 0, compute on the subset
    expected = compute_metric(MetricName.SPEARMAN, labels[1:], scores[1:])
    assert compute_metric(MetricName.SPEARMAN, labels, scores, weights=weights) == pytest.approx(
        expected
    )


def test_mismatched_label_prediction_lengths_raise() -> None:
    with pytest.raises(ValueError):
        compute_metric(MetricName.ACCURACY, np.array([0.0, 1.0]), np.array([0.5]))


def test_mismatched_weights_shape_raises() -> None:
    with pytest.raises(ValueError):
        compute_metric(
            MetricName.ACCURACY, np.array([0.0, 1.0]), np.array([0.2, 0.8]), weights=np.array([1.0])
        )
