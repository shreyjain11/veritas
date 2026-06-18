"""Performance-vs-difficulty figures as self-contained, deterministic SVG.

Matplotlib's nondeterministic SVG metadata is neutralized: a fixed ``svg.hashsalt``
makes element ids stable and ``metadata={"Date": None}`` drops the timestamp, so two
renders of the same curve are byte-identical (determinism gate).
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")  # headless: no display, no network

import matplotlib.pyplot as plt

from veritas.contracts import ResultStatus
from veritas.stratify import StratifiedCurve


def render_curve_svg(curve: StratifiedCurve, *, title: str | None = None) -> str:
    xs: list[int] = []
    ys: list[float] = []
    err_low: list[float] = []
    err_high: list[float] = []
    for bucket in curve.buckets:
        estimate = bucket.estimate
        if estimate.status is ResultStatus.OK and estimate.value is not None:
            low = estimate.ci_low if estimate.ci_low is not None else estimate.value
            high = estimate.ci_high if estimate.ci_high is not None else estimate.value
            xs.append(bucket.index)
            ys.append(estimate.value)
            # Error-bar offsets must be non-negative; a percentile-bootstrap CI need
            # not bracket the point estimate, so clamp rather than let matplotlib raise.
            err_low.append(max(0.0, estimate.value - low))
            err_high.append(max(0.0, high - estimate.value))

    figure, axes = plt.subplots(figsize=(4.0, 3.0))
    try:
        if xs:
            axes.errorbar(xs, ys, yerr=[err_low, err_high], marker="o", capsize=3)
        if curve.aggregate.status is ResultStatus.OK and curve.aggregate.value is not None:
            axes.axhline(curve.aggregate.value, linestyle="--", label="aggregate")
            axes.legend()
        axes.set_xlabel(curve.axis_name)
        axes.set_ylabel(curve.metric.value)
        axes.set_title(title if title is not None else f"{curve.metric.value} by {curve.axis_name}")
        buffer = io.StringIO()
        with matplotlib.rc_context({"svg.hashsalt": "veritas"}):
            figure.savefig(buffer, format="svg", metadata={"Date": None})
    finally:
        plt.close(figure)  # always release the figure, even if savefig raises
    return buffer.getvalue()
