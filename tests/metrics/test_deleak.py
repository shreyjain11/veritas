"""De-leak policies: drop (default), reweight, stratify."""

from __future__ import annotations

import pytest

from veritas.contracts import (
    ContaminationEdge,
    ContaminationGraph,
    DetectorKind,
    EvalItem,
    SeqType,
)
from veritas.metrics import drop, reweight, stratify


def _items(ids: tuple[str, ...]) -> tuple[EvalItem, ...]:
    return tuple(
        EvalItem(id=i, sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.9)
        for i in ids
    )


def _graph(contaminated: tuple[str, ...]) -> ContaminationGraph:
    return ContaminationGraph(
        edges=tuple(
            ContaminationEdge(
                eval_id=i, ref_id="r", score=1.0, kind=DetectorKind.SEQUENCE, detector_id="t"
            )
            for i in contaminated
        )
    )


def test_drop_removes_exactly_the_contaminated_items_preserving_order() -> None:
    items = _items(("a", "b", "c", "d"))
    kept = drop(items, _graph(("b", "d")))
    assert [item.id for item in kept] == ["a", "c"]


def test_reweight_assigns_fractional_weight_by_contamination_severity() -> None:
    # weight = 1 - (max identity-to-nearest-contaminating-reference); genuinely fractional.
    items = _items(("clean", "borderline", "near_dup"))
    graph = ContaminationGraph(
        edges=(
            ContaminationEdge(
                eval_id="borderline",
                ref_id="r",
                score=0.7,
                kind=DetectorKind.SEQUENCE,
                detector_id="t",
            ),
            ContaminationEdge(
                eval_id="near_dup",
                ref_id="r",
                score=1.0,
                kind=DetectorKind.SEQUENCE,
                detector_id="t",
            ),
        )
    )
    weights = reweight(items, graph)
    assert weights["clean"] == pytest.approx(1.0)
    assert weights["borderline"] == pytest.approx(0.3)  # 1 - 0.7
    assert weights["near_dup"] == pytest.approx(0.0)  # 1 - 1.0


def test_reweight_uses_max_severity_across_edges() -> None:
    items = _items(("multi",))
    graph = ContaminationGraph(
        edges=(
            ContaminationEdge(
                eval_id="multi", ref_id="r1", score=0.5, kind=DetectorKind.SEQUENCE, detector_id="t"
            ),
            ContaminationEdge(
                eval_id="multi", ref_id="r2", score=0.8, kind=DetectorKind.SEQUENCE, detector_id="t"
            ),
        )
    )
    assert reweight(items, graph)["multi"] == pytest.approx(0.2)  # 1 - max(0.5, 0.8)


def test_stratify_partitions_into_clean_and_contaminated() -> None:
    items = _items(("a", "b", "c", "d"))
    strata = stratify(items, _graph(("a", "c")))
    assert [item.id for item in strata["contaminated"]] == ["a", "c"]
    assert [item.id for item in strata["clean"]] == ["b", "d"]
