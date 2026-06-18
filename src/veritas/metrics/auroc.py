"""Hand-rolled AUROC (weighted, tie-aware), matching scikit-learn's algorithm."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from veritas.metrics.errors import UndefinedMetricError

FloatArray = NDArray[np.float64]


def auroc(labels: FloatArray, scores: FloatArray, weights: FloatArray) -> float:
    order = np.argsort(-scores, kind="mergesort")
    y, sorted_scores, w = labels[order], scores[order], weights[order]

    tps = np.cumsum(w * y)
    fps = np.cumsum(w * (1.0 - y))
    distinct = np.where(np.diff(sorted_scores))[0]
    thresholds = np.r_[distinct, sorted_scores.size - 1]
    tps = np.r_[0.0, tps[thresholds]]
    fps = np.r_[0.0, fps[thresholds]]

    total_pos, total_neg = tps[-1], fps[-1]
    if total_pos <= 0.0 or total_neg <= 0.0:
        raise UndefinedMetricError("AUROC is undefined when a class has no (weighted) members")
    tpr = tps / total_pos
    fpr = fps / total_neg
    return float(np.trapezoid(tpr, fpr))
