"""Honest-comparison edge cases (req B): zero and total contamination, no NaN/crash."""

from __future__ import annotations

import pytest

from tests.factories import make_inflation_construction
from veritas.contracts import (
    ContaminationEdge,
    ContaminationGraph,
    DeLeakPolicy,
    DetectorKind,
    EvalItem,
    MetricName,
    MetricSpec,
    ResultStatus,
    SeqType,
)
from veritas.metrics import UndefinedMetricError, compute_honest

_SPEC = MetricSpec(name=MetricName.ACCURACY, threshold=0.5)


def test_zero_contamination_makes_honest_equal_reported() -> None:
    case = make_inflation_construction()
    result = compute_honest(
        case.eval_items,
        ContaminationGraph(edges=()),
        _SPEC,
        policy=DeLeakPolicy.DROP,
        bootstrap_n=100,
        ci_level=0.95,
        seed=1729,
    )
    assert result.status is ResultStatus.OK
    assert result.n_contaminated == 0
    assert result.honest.value == pytest.approx(result.reported.value)
    assert result.delta.value == pytest.approx(0.0)


def test_total_contamination_yields_insufficient_clean_data() -> None:
    case = make_inflation_construction()
    all_contaminated = ContaminationGraph(
        edges=tuple(
            ContaminationEdge(
                eval_id=item.id, ref_id="r", score=1.0, kind=DetectorKind.SEQUENCE, detector_id="t"
            )
            for item in case.eval_items
        )
    )
    result = compute_honest(
        case.eval_items,
        all_contaminated,
        _SPEC,
        policy=DeLeakPolicy.DROP,
        bootstrap_n=100,
        ci_level=0.95,
        seed=1729,
    )
    assert result.status is ResultStatus.INSUFFICIENT_CLEAN_DATA
    assert result.n_clean == 0
    assert result.honest.status is ResultStatus.INSUFFICIENT_CLEAN_DATA
    assert result.honest.value is None
    assert result.delta.value is None  # explicit status, never NaN


def test_missing_prediction_raises() -> None:
    items = (
        EvalItem(id="a", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0),
    )  # no prediction
    with pytest.raises(ValueError):
        compute_honest(
            items,
            ContaminationGraph(edges=()),
            _SPEC,
            policy=DeLeakPolicy.DROP,
            bootstrap_n=10,
            ci_level=0.95,
            seed=1,
        )


def test_undefined_metric_propagates_to_status() -> None:
    # Single-class labels -> AUROC undefined -> graceful status, never a crash/NaN.
    items = tuple(
        EvalItem(
            id=f"e{i}", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.1 * i
        )
        for i in range(4)
    )
    spec = MetricSpec(name=MetricName.AUROC)
    result = compute_honest(
        items,
        ContaminationGraph(edges=()),
        spec,
        policy=DeLeakPolicy.DROP,
        bootstrap_n=10,
        ci_level=0.95,
        seed=1,
    )
    assert result.status is ResultStatus.UNDEFINED_METRIC
    assert result.reported.value is None


def test_honest_with_auroc_skips_degenerate_resamples() -> None:
    # AUROC honest path: clean subset has both classes (point defined), but some
    # bootstrap resamples are single-class and are skipped — estimates still produced.
    clean = [
        EvalItem(id="kp1", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.9),
        EvalItem(id="kp2", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.8),
        EvalItem(id="kn1", sequence="MKV", seq_type=SeqType.PROTEIN, label=0.0, prediction=0.2),
        EvalItem(id="kn2", sequence="MKV", seq_type=SeqType.PROTEIN, label=0.0, prediction=0.1),
    ]
    contaminated = [
        EvalItem(id="cp", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.7),
        EvalItem(id="cn", sequence="MKV", seq_type=SeqType.PROTEIN, label=0.0, prediction=0.3),
    ]
    graph = ContaminationGraph(
        edges=tuple(
            ContaminationEdge(
                eval_id=i, ref_id="r", score=1.0, kind=DetectorKind.SEQUENCE, detector_id="t"
            )
            for i in ("cp", "cn")
        )
    )
    result = compute_honest(
        tuple(clean + contaminated),
        graph,
        MetricSpec(name=MetricName.AUROC),
        policy=DeLeakPolicy.DROP,
        bootstrap_n=300,
        ci_level=0.95,
        seed=3,
    )
    assert result.status is ResultStatus.OK
    assert result.reported.value is not None
    assert result.honest.value is not None


def test_reweight_with_correlation_metric_raises_instead_of_falling_back() -> None:
    # Fractional reweight is undefined for rank/correlation metrics; compute_honest
    # must raise a clear error, NOT silently revert to drop.
    items = (
        EvalItem(id="a", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.2),
        EvalItem(id="b", sequence="MKV", seq_type=SeqType.PROTEIN, label=2.0, prediction=0.8),
        EvalItem(id="c", sequence="MKV", seq_type=SeqType.PROTEIN, label=3.0, prediction=0.9),
    )
    graph = ContaminationGraph(
        edges=(
            ContaminationEdge(
                eval_id="b", ref_id="r", score=0.7, kind=DetectorKind.SEQUENCE, detector_id="t"
            ),
        )
    )
    spec = MetricSpec(name=MetricName.SPEARMAN)
    with pytest.raises(UndefinedMetricError):
        compute_honest(
            items, graph, spec, policy=DeLeakPolicy.REWEIGHT, bootstrap_n=50, ci_level=0.95, seed=1
        )
