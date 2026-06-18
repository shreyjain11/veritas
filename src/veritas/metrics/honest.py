"""Reported-vs-honest comparison with a paired-bootstrap delta CI."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from veritas.contracts import (
    ContaminationGraph,
    DeLeakPolicy,
    EvalItem,
    MetricName,
    MetricSpec,
    ResultStatus,
)
from veritas.metrics.bootstrap import bootstrap_ci
from veritas.metrics.deleak import severity_by_eval
from veritas.metrics.errors import UndefinedMetricError
from veritas.metrics.registry import compute_metric
from veritas.metrics.result import HonestComparison, MetricEstimate

FloatArray = npt.NDArray[np.float64]
_CORRELATION_METRICS = frozenset({MetricName.SPEARMAN, MetricName.PEARSON})


def _honest_weight(item_id: str, severity: dict[str, float], policy: DeLeakPolicy) -> float:
    if item_id not in severity:
        return 1.0
    if policy is DeLeakPolicy.REWEIGHT:
        return 1.0 - min(1.0, severity[item_id])
    return 0.0  # drop / stratify: contaminated items excluded from the honest set


def _ci(samples: list[float], ci_level: float) -> tuple[float | None, float | None]:
    if not samples:  # pragma: no cover - defensive; a defined point yields >=1 valid resample
        return None, None
    arr = np.asarray(samples, dtype=np.float64)
    alpha = (1.0 - ci_level) / 2.0
    return float(np.quantile(arr, alpha)), float(np.quantile(arr, 1.0 - alpha))


def compute_honest(
    eval_items: Sequence[EvalItem],
    graph: ContaminationGraph,
    metric_spec: MetricSpec,
    *,
    policy: DeLeakPolicy = DeLeakPolicy.DROP,
    bootstrap_n: int = 1000,
    ci_level: float = 0.95,
    seed: int,
) -> HonestComparison:
    name = metric_spec.name
    threshold = metric_spec.threshold if metric_spec.threshold is not None else 0.5

    # Configuration error (not a data condition): rank/correlation metrics cannot be
    # fractionally reweighted. Raise loudly rather than silently reverting to drop.
    if policy is DeLeakPolicy.REWEIGHT and name in _CORRELATION_METRICS:
        raise UndefinedMetricError(
            f"fractional reweighting is undefined for {name}; use the drop or stratify policy"
        )

    labels_list: list[float] = []
    predictions_list: list[float] = []
    for item in eval_items:
        if item.prediction is None:
            raise ValueError(f"eval item {item.id!r} has no prediction; cannot compute a metric")
        labels_list.append(item.label)
        predictions_list.append(item.prediction)
    labels = np.asarray(labels_list, dtype=np.float64)
    predictions = np.asarray(predictions_list, dtype=np.float64)

    severity = severity_by_eval(graph)
    n_eval = len(eval_items)
    n_contaminated = sum(1 for item in eval_items if item.id in severity)
    n_clean = n_eval - n_contaminated
    weights = np.asarray(
        [_honest_weight(item.id, severity, policy) for item in eval_items], dtype=np.float64
    )

    def _comparison(
        reported: MetricEstimate,
        honest: MetricEstimate,
        delta: MetricEstimate,
        status: ResultStatus,
    ) -> HonestComparison:
        return HonestComparison(
            metric=name,
            reported=reported,
            honest=honest,
            delta=delta,
            n_eval=n_eval,
            n_contaminated=n_contaminated,
            n_clean=n_clean,
            status=status,
        )

    # The metric itself may be undefined on this data (e.g. AUROC on single-class labels).
    try:
        reported_point = compute_metric(name, labels, predictions, threshold=threshold)
    except UndefinedMetricError:
        undefined = MetricEstimate(value=None, status=ResultStatus.UNDEFINED_METRIC)
        return _comparison(undefined, undefined, undefined, ResultStatus.UNDEFINED_METRIC)

    if float(weights.sum()) == 0.0:
        reported_ci = bootstrap_ci(
            lambda y, p: compute_metric(name, y, p, threshold=threshold),
            labels,
            predictions,
            n=bootstrap_n,
            ci_level=ci_level,
            seed=seed,
        )
        reported = MetricEstimate(
            value=reported_point, ci_low=reported_ci[0], ci_high=reported_ci[1]
        )
        insufficient = MetricEstimate(value=None, status=ResultStatus.INSUFFICIENT_CLEAN_DATA)
        return _comparison(
            reported, insufficient, insufficient, ResultStatus.INSUFFICIENT_CLEAN_DATA
        )

    honest_point = compute_metric(name, labels, predictions, threshold=threshold, weights=weights)
    delta_point = reported_point - honest_point

    rng = np.random.default_rng(seed)
    reported_samples: list[float] = []
    honest_samples: list[float] = []
    delta_samples: list[float] = []
    for _ in range(bootstrap_n):
        idx = rng.integers(0, n_eval, n_eval)
        resampled_weights = weights[idx]
        if float(resampled_weights.sum()) == 0.0:
            continue
        try:
            reported_resample = compute_metric(
                name, labels[idx], predictions[idx], threshold=threshold
            )
            honest_resample = compute_metric(
                name, labels[idx], predictions[idx], threshold=threshold, weights=resampled_weights
            )
        except UndefinedMetricError:
            continue
        reported_samples.append(reported_resample)
        honest_samples.append(honest_resample)
        delta_samples.append(reported_resample - honest_resample)

    reported_low, reported_high = _ci(reported_samples, ci_level)
    honest_low, honest_high = _ci(honest_samples, ci_level)
    delta_low, delta_high = _ci(delta_samples, ci_level)
    return _comparison(
        MetricEstimate(value=reported_point, ci_low=reported_low, ci_high=reported_high),
        MetricEstimate(value=honest_point, ci_low=honest_low, ci_high=honest_high),
        MetricEstimate(value=delta_point, ci_low=delta_low, ci_high=delta_high),
        ResultStatus.OK,
    )
