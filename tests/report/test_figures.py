"""(d) Matplotlib SVG figures: valid, inline, and deterministic.

The performance-vs-difficulty curve renders to a self-contained SVG string with
nondeterministic metadata (timestamps, element ids) stripped, so two renders of
the same curve are byte-identical (determinism gate).
"""

from __future__ import annotations

from tests.conftest import DEFAULT_SEED
from tests.factories import make_failure_regime
from veritas.contracts import (
    ContaminationEdge,
    ContaminationGraph,
    DetectorKind,
    EvalItem,
    MetricName,
    MetricSpec,
    SeqType,
)
from veritas.metrics import MetricEstimate
from veritas.report import render_curve_svg
from veritas.stratify import (
    StratifiedCurve,
    fixed_bins,
    identity_to_nearest_reference,
    performance_curve,
)
from veritas.stratify.curves import BucketResult


def _curve() -> StratifiedCurve:
    regime = make_failure_regime()
    axis = identity_to_nearest_reference(regime.eval_items, regime.graph)
    return performance_curve(
        regime.eval_items,
        axis,
        fixed_bins(regime.n_bins, lo=0.0, hi=1.0),
        MetricSpec(name=MetricName.ACCURACY),
        seed=DEFAULT_SEED,
        n_bootstrap=50,
    )


def _auroc_curve(items: tuple[EvalItem, ...], edges: list[ContaminationEdge]) -> StratifiedCurve:
    graph = ContaminationGraph(edges=tuple(edges))
    axis = identity_to_nearest_reference(items, graph)
    return performance_curve(
        items,
        axis,
        fixed_bins(4, lo=0.0, hi=1.0),
        MetricSpec(name=MetricName.AUROC),
        seed=DEFAULT_SEED,
        n_bootstrap=20,
    )


def _item(item_id: str, label: float, prediction: float) -> EvalItem:
    return EvalItem(
        id=item_id, sequence="MKV", seq_type=SeqType.PROTEIN, label=label, prediction=prediction
    )


def _edge(eval_id: str) -> ContaminationEdge:
    return ContaminationEdge(
        eval_id=eval_id, ref_id="r", score=0.9, kind=DetectorKind.SEQUENCE, detector_id="d"
    )


def test_curve_renders_valid_svg() -> None:
    svg = render_curve_svg(_curve())
    assert "<svg" in svg


def test_curve_svg_is_deterministic() -> None:
    curve = _curve()
    assert render_curve_svg(curve) == render_curve_svg(curve)


def test_curve_svg_accepts_a_title() -> None:
    assert "<svg" in render_curve_svg(_curve(), title="custom title")


def test_curve_svg_skips_undefined_buckets() -> None:
    # bucket 0 defined (both classes), bucket 3 undefined (single class) -> skipped.
    items = (
        _item("a0", 0.0, 0.1),
        _item("a1", 1.0, 0.9),
        _item("d0", 1.0, 0.5),
        _item("d1", 1.0, 0.6),
    )
    svg = render_curve_svg(_auroc_curve(items, [_edge("d0"), _edge("d1")]))
    assert "<svg" in svg


def test_curve_svg_handles_all_undefined_buckets() -> None:
    # Every bucket and the aggregate are undefined (single-class AUROC): no points,
    # no aggregate line -- still a valid SVG, no crash.
    items = (_item("a0", 1.0, 0.4), _item("a1", 1.0, 0.6), _item("d0", 1.0, 0.5))
    curve = _auroc_curve(items, [_edge("d0")])
    assert "<svg" in render_curve_svg(curve)


def test_curve_svg_tolerates_point_estimate_outside_ci() -> None:
    # A percentile-bootstrap CI need not bracket the point estimate; the resulting
    # negative error-bar offset must be clamped, not crash matplotlib.
    bucket = BucketResult(
        index=0,
        lo=0.0,
        hi=0.25,
        n=10,
        estimate=MetricEstimate(value=0.3, ci_low=0.4, ci_high=0.8),
    )
    curve = StratifiedCurve(
        metric=MetricName.AUROC,
        axis_name="identity_to_nearest_reference",
        greater_is_better=True,
        buckets=(bucket,),
        aggregate=MetricEstimate(value=0.5, ci_low=0.4, ci_high=0.6),
    )
    assert "<svg" in render_curve_svg(curve)
