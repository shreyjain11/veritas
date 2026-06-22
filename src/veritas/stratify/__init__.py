"""Stratified robustness analysis: difficulty axes, curves, silent-failure flags."""

from __future__ import annotations

from veritas.stratify.axes import (
    identity_to_nearest_reference,
    label_class,
    metadata_category,
)
from veritas.stratify.binning import Bins, fixed_bins, quantile_bins
from veritas.stratify.curves import (
    BucketResult,
    StratifiedCurve,
    categorical_performance_curve,
    performance_curve,
)
from veritas.stratify.silent_failure import SilentFailureFlag, detect_silent_failures

__all__ = [
    "Bins",
    "BucketResult",
    "SilentFailureFlag",
    "StratifiedCurve",
    "categorical_performance_curve",
    "detect_silent_failures",
    "fixed_bins",
    "identity_to_nearest_reference",
    "label_class",
    "metadata_category",
    "performance_curve",
    "quantile_bins",
]
