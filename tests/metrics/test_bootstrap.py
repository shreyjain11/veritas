"""Bootstrap confidence intervals: determinism, Monte-Carlo coverage, shrink with size."""

from __future__ import annotations

from collections.abc import Callable
from math import erf

import numpy as np
import pytest
from numpy.typing import NDArray

from veritas.contracts import MetricName
from veritas.metrics import UndefinedMetricError, bootstrap_ci, compute_metric


def _mean_prediction(labels: NDArray[np.float64], predictions: NDArray[np.float64]) -> float:
    return float(np.mean(predictions))


def _auroc(labels: NDArray[np.float64], predictions: NDArray[np.float64]) -> float:
    return compute_metric(MetricName.AUROC, labels, predictions)


def test_bootstrap_ci_is_deterministic() -> None:
    rng = np.random.default_rng(0)
    predictions = rng.normal(size=50)
    labels = np.zeros(50)
    first = bootstrap_ci(_mean_prediction, labels, predictions, n=200, ci_level=0.95, seed=1)
    second = bootstrap_ci(_mean_prediction, labels, predictions, n=200, ci_level=0.95, seed=1)
    assert first == second


# --- Monte-Carlo coverage --------------------------------------------------
#
# A percentile-bootstrap CI almost always brackets *its own sample statistic*,
# so the old "contains point estimate" check was near-tautological (it passed for
# any sane interval, even a too-narrow one). The real contract is *frequentist
# coverage*: over many datasets drawn from a distribution with a KNOWN population
# parameter, the nominal-95% CI should bracket the TRUE value about 95% of the
# time. These bands are set to what the percentile method EMPIRICALLY delivers,
# not an idealized 0.95: it mildly under-covers at small n (measured mean coverage
# 0.927@n=25 -> 0.944@n=80, AUROC 0.938@n=40 -> 0.948@n=200) and converges upward.
# The floor fails a collapsed/too-narrow CI (coverage -> 0); the ceiling fails a
# degenerate over-wide CI (coverage -> 1). Deterministic: one pinned master seed.

_COVERAGE_SEED = 2024
_CI_LEVEL = 0.95
#: Two-sided acceptance band for well-behaved statistics (the mean).
_COVERAGE_FLOOR = 0.90
_COVERAGE_CEIL = 0.98

_TRUE_MEAN = 0.3
#: True AUROC for two unit-variance Gaussians separated by ``delta`` is
#: ``P(X_pos > X_neg) = Phi(delta / sqrt(2))``; for delta=1 this is 0.7602.
_AUROC_SEPARATION = 1.0
_TRUE_AUROC = 0.5 * (1.0 + erf(_AUROC_SEPARATION / 2.0))

_FloatArray = NDArray[np.float64]
_Dataset = Callable[[np.random.Generator], tuple[_FloatArray, _FloatArray]]
_Statistic = Callable[[_FloatArray, _FloatArray], float]


def _normal_mean_dataset(n: int) -> _Dataset:
    def make(rng: np.random.Generator) -> tuple[_FloatArray, _FloatArray]:
        predictions = rng.normal(_TRUE_MEAN, 1.0, size=n)
        return np.zeros(n), predictions

    return make


def _gaussian_auroc_dataset(n: int) -> _Dataset:
    def make(rng: np.random.Generator) -> tuple[_FloatArray, _FloatArray]:
        half = n // 2
        labels = np.concatenate([np.zeros(half), np.ones(n - half)])
        scores = np.concatenate(
            [rng.normal(0.0, 1.0, half), rng.normal(_AUROC_SEPARATION, 1.0, n - half)]
        )
        return labels, scores

    return make


def _empirical_coverage(
    statistic: _Statistic,
    true_value: float,
    make_dataset: _Dataset,
    *,
    n_datasets: int,
    n_resamples: int,
) -> tuple[float, float]:
    """Fraction of CIs that bracket ``true_value`` and the mean CI width."""
    rng = np.random.default_rng(_COVERAGE_SEED)
    covered = 0
    total_width = 0.0
    for trial in range(n_datasets):
        labels, predictions = make_dataset(rng)
        low, high = bootstrap_ci(
            statistic, labels, predictions, n=n_resamples, ci_level=_CI_LEVEL, seed=trial
        )
        covered += int(low <= true_value <= high)
        total_width += high - low
    return covered / n_datasets, total_width / n_datasets


def test_bootstrap_ci_coverage_is_near_nominal_for_mean() -> None:
    """Frequentist coverage of the true population mean ~= ci_level, width shrinks with n.

    Measured with the pinned seed: coverage 0.938 @ n=50, 0.953 @ n=150.
    """
    cov_small, width_small = _empirical_coverage(
        _mean_prediction, _TRUE_MEAN, _normal_mean_dataset(50), n_datasets=600, n_resamples=300
    )
    cov_large, width_large = _empirical_coverage(
        _mean_prediction, _TRUE_MEAN, _normal_mean_dataset(150), n_datasets=600, n_resamples=300
    )
    assert _COVERAGE_FLOOR <= cov_small <= _COVERAGE_CEIL
    assert _COVERAGE_FLOOR <= cov_large <= _COVERAGE_CEIL
    assert width_large < width_small


def test_bootstrap_ci_coverage_for_skewed_auroc_is_documented() -> None:
    """FINDING: percentile-bootstrap coverage for the skewed AUROC statistic.

    Measured with the pinned seed: coverage 0.942 @ n=100 (true AUROC 0.7602) -- close to
    nominal with the mild under-coverage expected of the percentile method. We assert a
    DELIBERATELY LOOSE band rather than nominal 0.95: this reports what the method delivers
    instead of over-claiming, while the floor still fails a collapsed/narrow CI.
    """
    coverage, _ = _empirical_coverage(
        _auroc, _TRUE_AUROC, _gaussian_auroc_dataset(100), n_datasets=500, n_resamples=250
    )
    assert 0.88 <= coverage <= 0.99


def test_bootstrap_ci_narrows_with_more_data() -> None:
    rng = np.random.default_rng(2)
    small = rng.normal(size=25)
    large = rng.normal(size=2500)
    low_s, high_s = bootstrap_ci(
        _mean_prediction, np.zeros(25), small, n=400, ci_level=0.95, seed=3
    )
    low_l, high_l = bootstrap_ci(
        _mean_prediction, np.zeros(2500), large, n=400, ci_level=0.95, seed=3
    )
    assert (high_l - low_l) < (high_s - low_s)


def test_bootstrap_skips_degenerate_resamples() -> None:
    # A small binary set: some resamples are single-class (AUROC undefined) and are
    # skipped, but a CI is still produced from the valid resamples.
    labels = np.array([0.0, 0.0, 1.0, 1.0])
    scores = np.array([0.1, 0.2, 0.8, 0.9])
    low, high = bootstrap_ci(_auroc, labels, scores, n=200, ci_level=0.95, seed=7)
    assert low <= high


def test_bootstrap_raises_when_all_resamples_degenerate() -> None:
    labels = np.array([1.0])  # every resample is the same single-class point
    scores = np.array([0.5])
    with pytest.raises(UndefinedMetricError):
        bootstrap_ci(_auroc, labels, scores, n=50, ci_level=0.95, seed=1)
