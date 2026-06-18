"""Metric error types."""

from __future__ import annotations


class UndefinedMetricError(Exception):
    """Raised when a metric is mathematically undefined for the given inputs.

    Examples: AUROC on single-class labels, average precision with no positives,
    correlation on constant input, or fractional weights for a rank/correlation
    metric. The audit layer maps this to ``ResultStatus.UNDEFINED_METRIC`` for
    data conditions, and lets configuration errors (e.g. reweight + correlation)
    propagate.
    """
