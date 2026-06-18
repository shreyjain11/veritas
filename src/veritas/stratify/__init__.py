"""Stratified robustness analysis: difficulty axes, curves, silent-failure flags."""

from __future__ import annotations

from veritas.stratify.axes import identity_to_nearest_reference, label_class
from veritas.stratify.binning import Bins, fixed_bins, quantile_bins
from veritas.stratify.curves import BucketResult, StratifiedCurve, performance_curve
from veritas.stratify.silent_failure import SilentFailureFlag, detect_silent_failures

__all__ = [
    "Bins",
    "BucketResult",
    "SilentFailureFlag",
    "StratifiedCurve",
    "detect_silent_failures",
    "fixed_bins",
    "identity_to_nearest_reference",
    "label_class",
    "performance_curve",
    "quantile_bins",
]
