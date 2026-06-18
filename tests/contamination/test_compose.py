"""Multi-detector composition: union/intersect via CombinePolicy."""

from __future__ import annotations

from veritas.contamination.compose import combine
from veritas.contracts import (
    CombinePolicy,
    ContaminationEdge,
    ContaminationGraph,
    DetectorKind,
)


def _edge(eval_id: str, ref_id: str, kind: DetectorKind, detector_id: str) -> ContaminationEdge:
    return ContaminationEdge(
        eval_id=eval_id, ref_id=ref_id, score=0.9, kind=kind, detector_id=detector_id
    )


_SEQ = _edge("e1", "r1", DetectorKind.SEQUENCE, "mmseqs")
_STRUCT_SHARED = _edge("e1", "r1", DetectorKind.STRUCTURE, "foldseek")
_STRUCT_OTHER = _edge("e2", "r2", DetectorKind.STRUCTURE, "foldseek")


def test_union_keeps_all_edges() -> None:
    seq = ContaminationGraph(edges=(_SEQ,))
    struct = ContaminationGraph(edges=(_STRUCT_SHARED, _STRUCT_OTHER))
    result = combine((seq, struct), CombinePolicy.UNION)
    assert {(e.eval_id, e.ref_id, e.kind) for e in result.edges} == {
        ("e1", "r1", DetectorKind.SEQUENCE),
        ("e1", "r1", DetectorKind.STRUCTURE),
        ("e2", "r2", DetectorKind.STRUCTURE),
    }


def test_intersect_keeps_only_pairs_flagged_by_all() -> None:
    seq = ContaminationGraph(edges=(_SEQ,))
    struct = ContaminationGraph(edges=(_STRUCT_SHARED, _STRUCT_OTHER))
    result = combine((seq, struct), CombinePolicy.INTERSECT)
    assert {(e.eval_id, e.ref_id) for e in result.edges} == {("e1", "r1")}


def test_single_graph_union_equals_intersect() -> None:
    only = ContaminationGraph(edges=(_SEQ,))
    assert (
        combine((only,), CombinePolicy.UNION).edges
        == combine((only,), CombinePolicy.INTERSECT).edges
    )
