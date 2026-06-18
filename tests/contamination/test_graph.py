"""ContaminationGraph operations: union, intersect, filter, nearest, contaminated set."""

from __future__ import annotations

from veritas.contamination.graph import (
    contaminated_eval_ids,
    filter_by_score,
    intersect,
    nearest_score_by_eval,
    union,
)
from veritas.contracts import ContaminationEdge, ContaminationGraph, DetectorKind


def _edge(eval_id: str, ref_id: str, score: float, detector_id: str = "m") -> ContaminationEdge:
    return ContaminationEdge(
        eval_id=eval_id,
        ref_id=ref_id,
        score=score,
        kind=DetectorKind.SEQUENCE,
        detector_id=detector_id,
    )


def _graph(*edges: ContaminationEdge) -> ContaminationGraph:
    return ContaminationGraph(edges=edges)


def test_union_is_superset_and_dedups() -> None:
    g1 = _graph(_edge("e1", "r1", 0.9))
    g2 = _graph(_edge("e1", "r1", 0.9), _edge("e2", "r2", 0.8))
    result = union(g1, g2)
    pairs = {(e.eval_id, e.ref_id) for e in result.edges}
    assert pairs == {("e1", "r1"), ("e2", "r2")}  # duplicate edge collapsed


def test_intersect_keeps_pairs_present_in_all() -> None:
    g1 = _graph(_edge("e1", "r1", 0.9), _edge("e2", "r2", 0.8))
    g2 = _graph(_edge("e1", "r1", 0.7))
    result = intersect(g1, g2)
    assert {(e.eval_id, e.ref_id) for e in result.edges} == {("e1", "r1")}


def test_filter_by_score_drops_below_threshold() -> None:
    result = filter_by_score(_graph(_edge("e1", "r1", 0.9), _edge("e2", "r2", 0.4)), 0.5)
    assert {(e.eval_id, e.ref_id) for e in result.edges} == {("e1", "r1")}


def test_contaminated_eval_ids() -> None:
    assert contaminated_eval_ids(
        _graph(_edge("e1", "r1", 0.9), _edge("e1", "r2", 0.6))
    ) == frozenset({"e1"})


def test_nearest_score_by_eval_takes_max() -> None:
    graph = _graph(_edge("e1", "r1", 0.6), _edge("e1", "r2", 0.95), _edge("e2", "r3", 0.4))
    assert nearest_score_by_eval(graph) == {"e1": 0.95, "e2": 0.4}


def test_nearest_score_keeps_max_when_later_edge_is_lower() -> None:
    graph = _graph(_edge("e1", "r1", 0.9), _edge("e1", "r2", 0.4))
    assert nearest_score_by_eval(graph) == {"e1": 0.9}


def test_intersect_with_no_graphs_is_empty() -> None:
    assert intersect().edges == ()
