"""Phase-3 result types (converted to report-level TracedValues in Phase 6)."""

from __future__ import annotations

from veritas.contracts import MetricName, ResultStatus
from veritas.contracts.base import FrozenModel


class MetricEstimate(FrozenModel):
    value: float | None
    status: ResultStatus = ResultStatus.OK
    ci_low: float | None = None
    ci_high: float | None = None


class HonestComparison(FrozenModel):
    metric: MetricName
    reported: MetricEstimate
    honest: MetricEstimate
    delta: MetricEstimate
    n_eval: int
    n_contaminated: int
    n_clean: int
    status: ResultStatus = ResultStatus.OK
