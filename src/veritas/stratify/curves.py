"""Performance-vs-difficulty curves: a metric (+ bootstrap CI) per bucket.

Each eval item is placed in one difficulty bucket; the chosen metric is computed
per bucket and over the whole set (the aggregate), each with a Phase-3 bootstrap
CI. Buckets that cannot support a point estimate -- too few items, or a metric
undefined on the bucket -- carry an explicit ResultStatus and a ``None`` value
rather than a NaN.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import numpy.typing as npt

from veritas.contracts import EvalItem, MetricName, MetricSpec, ResultStatus
from veritas.contracts.base import FrozenModel
from veritas.metrics import MetricEstimate, UndefinedMetricError, bootstrap_ci, compute_metric
from veritas.stratify.binning import Bins

_FloatArray = npt.NDArray[np.float64]


class BucketResult(FrozenModel):
    index: int
    lo: float
    hi: float
    n: int
    estimate: MetricEstimate


class StratifiedCurve(FrozenModel):
    metric: MetricName
    axis_name: str
    greater_is_better: bool
    buckets: tuple[BucketResult, ...]
    aggregate: MetricEstimate
    status: ResultStatus = ResultStatus.OK


def _estimate(
    labels: _FloatArray,
    predictions: _FloatArray,
    name: MetricName,
    threshold: float,
    *,
    n_bootstrap: int,
    ci_level: float,
    seed: int,
    min_n: int,
) -> MetricEstimate:
    if labels.shape[0] < min_n:
        return MetricEstimate(value=None, status=ResultStatus.INSUFFICIENT_CLEAN_DATA)

    def metric(y: _FloatArray, p: _FloatArray) -> float:
        return compute_metric(name, y, p, threshold=threshold)

    try:
        value = metric(labels, predictions)
    except UndefinedMetricError:
        return MetricEstimate(value=None, status=ResultStatus.UNDEFINED_METRIC)
    try:
        low, high = bootstrap_ci(
            metric, labels, predictions, n=n_bootstrap, ci_level=ci_level, seed=seed
        )
    except (
        UndefinedMetricError
    ):  # pragma: no cover - defensive: a defined point yields >=1 valid resample
        low, high = None, None
    return MetricEstimate(value=value, status=ResultStatus.OK, ci_low=low, ci_high=high)


def performance_curve(
    eval_items: Sequence[EvalItem],
    axis_values: Mapping[str, float],
    bins: Bins,
    metric_spec: MetricSpec,
    *,
    axis_name: str = "identity_to_nearest_reference",
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    seed: int,
    min_bucket_n: int = 2,
) -> StratifiedCurve:
    name = metric_spec.name
    threshold = metric_spec.threshold if metric_spec.threshold is not None else 0.5
    n_bins = bins.n_bins()

    bucket_members: list[list[int]] = [[] for _ in range(n_bins)]
    labels_list: list[float] = []
    predictions_list: list[float] = []
    for i, item in enumerate(eval_items):
        if item.prediction is None:
            raise ValueError(f"eval item {item.id!r} has no prediction; cannot compute a metric")
        if item.id not in axis_values:
            raise ValueError(
                f"eval item {item.id!r} is missing from axis_values; cannot stratify it"
            )
        labels_list.append(item.label)
        predictions_list.append(item.prediction)
        bucket_members[bins.assign(axis_values[item.id])].append(i)
    labels = np.asarray(labels_list, dtype=np.float64)
    predictions = np.asarray(predictions_list, dtype=np.float64)

    def estimate(y: _FloatArray, p: _FloatArray, min_n: int) -> MetricEstimate:
        return _estimate(
            y,
            p,
            name,
            threshold,
            n_bootstrap=n_bootstrap,
            ci_level=ci_level,
            seed=seed,
            min_n=min_n,
        )

    buckets: list[BucketResult] = []
    for index in range(n_bins):
        rows = np.asarray(bucket_members[index], dtype=np.intp)
        buckets.append(
            BucketResult(
                index=index,
                lo=bins.edges[index],
                hi=bins.edges[index + 1],
                n=int(rows.size),
                estimate=estimate(labels[rows], predictions[rows], min_bucket_n),
            )
        )

    aggregate = estimate(labels, predictions, 1)
    return StratifiedCurve(
        metric=name,
        axis_name=axis_name,
        greater_is_better=metric_spec.greater_is_better,
        buckets=tuple(buckets),
        aggregate=aggregate,
        status=aggregate.status,
    )
