"""Thresholded binary classification metrics (weighted): accuracy, MCC, F1."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def _binarize(scores: FloatArray, threshold: float) -> FloatArray:
    return (scores >= threshold).astype(np.float64)


def accuracy(
    labels: FloatArray, scores: FloatArray, threshold: float, weights: FloatArray
) -> float:
    correct = (_binarize(scores, threshold) == labels).astype(np.float64)
    return float(np.average(correct, weights=weights))


def _confusion(
    labels: FloatArray, scores: FloatArray, threshold: float, weights: FloatArray
) -> tuple[float, float, float, float]:
    predicted = _binarize(scores, threshold)
    tp = float(np.sum(weights * (predicted == 1.0) * (labels == 1.0)))
    tn = float(np.sum(weights * (predicted == 0.0) * (labels == 0.0)))
    fp = float(np.sum(weights * (predicted == 1.0) * (labels == 0.0)))
    fn = float(np.sum(weights * (predicted == 0.0) * (labels == 1.0)))
    return tp, tn, fp, fn


def mcc(labels: FloatArray, scores: FloatArray, threshold: float, weights: FloatArray) -> float:
    tp, tn, fp, fn = _confusion(labels, scores, threshold, weights)
    denominator = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    if denominator == 0.0:  # degenerate (a row/column of the confusion matrix is empty)
        return 0.0
    return float((tp * tn - fp * fn) / denominator)


def f1(labels: FloatArray, scores: FloatArray, threshold: float, weights: FloatArray) -> float:
    tp, _tn, fp, fn = _confusion(labels, scores, threshold, weights)
    if tp == 0.0:  # precision or recall is 0 -> F1 = 0 (matches sklearn zero_division=0)
        return 0.0
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    return float(2.0 * precision * recall / (precision + recall))
