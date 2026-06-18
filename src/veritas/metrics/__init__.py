"""Metrics, bootstrap confidence intervals, de-leak policies, and honest comparison."""

from __future__ import annotations

from veritas.metrics.bootstrap import bootstrap_ci
from veritas.metrics.deleak import drop, reweight, severity_by_eval, stratify
from veritas.metrics.errors import UndefinedMetricError
from veritas.metrics.honest import compute_honest
from veritas.metrics.registry import compute_metric, requires_binary_labels
from veritas.metrics.result import HonestComparison, MetricEstimate

__all__ = [
    "HonestComparison",
    "MetricEstimate",
    "UndefinedMetricError",
    "bootstrap_ci",
    "compute_honest",
    "compute_metric",
    "drop",
    "requires_binary_labels",
    "reweight",
    "severity_by_eval",
    "stratify",
]
