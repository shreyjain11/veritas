"""Hand-rolled average precision (AUPRC), weighted, matching scikit-learn."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from veritas.metrics.errors import UndefinedMetricError

FloatArray = NDArray[np.float64]


def average_precision(labels: FloatArray, scores: FloatArray, weights: FloatArray) -> float:
    order = np.argsort(-scores, kind="mergesort")
    y, sorted_scores, w = labels[order], scores[order], weights[order]

    tps = np.cumsum(w * y)
    fps = np.cumsum(w * (1.0 - y))
    distinct = np.where(np.diff(sorted_scores))[0]
    thresholds = np.r_[distinct, sorted_scores.size - 1]
    tps = tps[thresholds]
    fps = fps[thresholds]

    total_pos = tps[-1]
    if total_pos <= 0.0:
        raise UndefinedMetricError(
            "average precision is undefined with no positive (weighted) members"
        )
    recall = tps / total_pos
    precision = tps / (tps + fps)
    recall_prev = np.r_[0.0, recall[:-1]]
    return float(np.sum((recall - recall_prev) * precision))
