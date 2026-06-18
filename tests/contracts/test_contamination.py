"""ContaminationEdge / ContaminationGraph: schema-only checks (engine is Phase 2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veritas.contracts import ContaminationEdge, ContaminationGraph, DetectorKind


def _edge(eval_id: str, ref_id: str, score: float = 0.9) -> ContaminationEdge:
    return ContaminationEdge(
        eval_id=eval_id,
        ref_id=ref_id,
        score=score,
        kind=DetectorKind.SEQUENCE,
        detector_id="mmseqs",
    )


def test_contamination_edge_valid() -> None:
    edge = _edge("e1", "r1")
    assert edge.eval_id == "e1"
    assert edge.kind is DetectorKind.SEQUENCE


def test_edge_score_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        _edge("e1", "r1", score=-0.1)


def test_graph_holds_edges() -> None:
    graph = ContaminationGraph(edges=(_edge("e1", "r1"), _edge("e2", "r2")))
    assert len(graph.edges) == 2


def test_graph_round_trip_json() -> None:
    graph = ContaminationGraph(edges=(_edge("e1", "r1"),))
    assert ContaminationGraph.model_validate_json(graph.model_dump_json()) == graph
