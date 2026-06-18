"""Rank/linear correlation metrics via scipy: Spearman, Pearson."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from veritas.metrics.errors import UndefinedMetricError

FloatArray = NDArray[np.float64]


def _require_variation(labels: FloatArray, predictions: FloatArray, name: str) -> None:
    if float(np.std(labels)) == 0.0 or float(np.std(predictions)) == 0.0:
        raise UndefinedMetricError(f"{name} is undefined for constant input")


def spearman(labels: FloatArray, predictions: FloatArray) -> float:
    _require_variation(labels, predictions, "Spearman")
    return float(stats.spearmanr(labels, predictions).statistic)


def pearson(labels: FloatArray, predictions: FloatArray) -> float:
    _require_variation(labels, predictions, "Pearson")
    return float(stats.pearsonr(labels, predictions).statistic)
