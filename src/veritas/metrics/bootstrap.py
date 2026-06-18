"""Seeded percentile bootstrap confidence intervals."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import numpy.typing as npt

from veritas.metrics.errors import UndefinedMetricError

FloatArray = npt.NDArray[np.float64]
Metric = Callable[[FloatArray, FloatArray], float]


def bootstrap_ci(
    metric: Metric,
    labels: npt.ArrayLike,
    predictions: npt.ArrayLike,
    *,
    n: int,
    ci_level: float,
    seed: int,
) -> tuple[float, float]:
    y = np.asarray(labels, dtype=np.float64)
    p = np.asarray(predictions, dtype=np.float64)
    rng = np.random.default_rng(seed)
    size = y.shape[0]

    estimates: list[float] = []
    for _ in range(n):
        idx = rng.integers(0, size, size)
        try:
            estimates.append(metric(y[idx], p[idx]))
        except UndefinedMetricError:
            continue
    if not estimates:
        raise UndefinedMetricError("every bootstrap resample was degenerate")

    samples = np.asarray(estimates, dtype=np.float64)
    alpha = (1.0 - ci_level) / 2.0
    return float(np.quantile(samples, alpha)), float(np.quantile(samples, 1.0 - alpha))
