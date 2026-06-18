"""Silent-failure flagging: difficulty buckets that quietly underperform.

A bucket is flagged when it is meaningfully *worse* than the aggregate and its
confidence interval separates it from the aggregate -- so a healthy headline that
hides a failing regime is surfaced, but ordinary difficulty variation (or a bucket
whose estimate is merely uncertain) is not. "Worse" follows the metric direction
(``greater_is_better``). Buckets and aggregates without an OK estimate are never
flagged.
"""

from __future__ import annotations

from veritas.contracts import ResultStatus
from veritas.contracts.base import FrozenModel
from veritas.stratify.curves import StratifiedCurve

#: Minimum gap (in metric units) between a bucket and the aggregate to flag it.
DEFAULT_MIN_GAP = 0.1


class SilentFailureFlag(FrozenModel):
    bucket_index: int
    bucket_value: float
    aggregate_value: float
    #: How far the bucket falls short of the aggregate (always non-negative).
    gap: float


def detect_silent_failures(
    curve: StratifiedCurve, *, min_gap: float = DEFAULT_MIN_GAP
) -> tuple[SilentFailureFlag, ...]:
    aggregate = curve.aggregate.value
    if curve.aggregate.status is not ResultStatus.OK or aggregate is None:
        return ()

    flags: list[SilentFailureFlag] = []
    for bucket in curve.buckets:
        estimate = bucket.estimate
        value, ci_low, ci_high = estimate.value, estimate.ci_low, estimate.ci_high
        if (
            estimate.status is not ResultStatus.OK
            or value is None
            or ci_low is None
            or ci_high is None
        ):
            continue
        if curve.greater_is_better:
            gap = aggregate - value
            ci_separated = ci_high < aggregate
        else:
            gap = value - aggregate
            ci_separated = ci_low > aggregate
        if gap >= min_gap and ci_separated:
            flags.append(
                SilentFailureFlag(
                    bucket_index=bucket.index,
                    bucket_value=value,
                    aggregate_value=aggregate,
                    gap=gap,
                )
            )
    return tuple(flags)
