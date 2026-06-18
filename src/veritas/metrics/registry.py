"""Metric registry: one entry point dispatching all metrics with a task-type guard."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from veritas.contracts import MetricName
from veritas.metrics.auprc import average_precision
from veritas.metrics.auroc import auroc
from veritas.metrics.classification import accuracy, f1, mcc
from veritas.metrics.correlation import pearson, spearman
from veritas.metrics.errors import UndefinedMetricError

FloatArray = npt.NDArray[np.float64]

_BINARY_LABEL_METRICS = frozenset(
    {MetricName.AUROC, MetricName.AUPRC, MetricName.ACCURACY, MetricName.MCC, MetricName.F1}
)
_CORRELATION_METRICS = frozenset({MetricName.SPEARMAN, MetricName.PEARSON})


def requires_binary_labels(name: MetricName) -> bool:
    return name in _BINARY_LABEL_METRICS


def _validate_binary(labels: FloatArray) -> None:
    if not np.all((labels == 0.0) | (labels == 1.0)):
        raise ValueError("binary-label metric requires labels in {0, 1}")


def _correlation_subset(
    labels: FloatArray, predictions: FloatArray, weights: FloatArray, name: MetricName
) -> tuple[FloatArray, FloatArray]:
    nonzero = weights[weights != 0.0]
    if nonzero.size > 0 and not np.allclose(nonzero, nonzero[0]):
        raise UndefinedMetricError(
            f"fractional weights are undefined for {name}; use the drop policy or stratify"
        )
    mask = weights > 0.0
    return labels[mask], predictions[mask]


def compute_metric(
    name: MetricName,
    labels: npt.ArrayLike,
    predictions: npt.ArrayLike,
    *,
    threshold: float = 0.5,
    weights: npt.ArrayLike | None = None,
) -> float:
    y = np.asarray(labels, dtype=np.float64)
    p = np.asarray(predictions, dtype=np.float64)
    if y.ndim != 1 or y.shape != p.shape:
        raise ValueError("labels and predictions must be 1-D arrays of equal length")
    if requires_binary_labels(name):
        _validate_binary(y)

    w = None if weights is None else np.asarray(weights, dtype=np.float64)
    if w is not None and w.shape != y.shape:
        raise ValueError("weights must have the same shape as labels")

    if name in _CORRELATION_METRICS:
        if w is not None:
            y, p = _correlation_subset(y, p, w, name)
        return spearman(y, p) if name is MetricName.SPEARMAN else pearson(y, p)

    weight = w if w is not None else np.ones_like(y)
    if name is MetricName.AUROC:
        return auroc(y, p, weight)
    if name is MetricName.AUPRC:
        return average_precision(y, p, weight)
    if name is MetricName.ACCURACY:
        return accuracy(y, p, threshold, weight)
    if name is MetricName.MCC:
        return mcc(y, p, threshold, weight)
    return f1(y, p, threshold, weight)
