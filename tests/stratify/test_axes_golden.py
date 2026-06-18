"""(a) Difficulty axes read straight from the ContaminationGraph edge scores.

The identity-to-nearest-reference axis must take its value from the graph edges
the Phase-2 detectors already produced -- it must NOT re-align or recompute
identity from the sequences. We prove that by planting an edge score that
disagrees with what a recompute on the (identical) sequences would yield and
asserting the axis returns the *edge* value.
"""

from __future__ import annotations

from veritas.contracts import (
    ContaminationEdge,
    ContaminationGraph,
    DetectorKind,
    EvalItem,
    SeqType,
)
from veritas.stratify import identity_to_nearest_reference, label_class


def _eval(item_id: str, label: float = 1.0) -> EvalItem:
    return EvalItem(
        id=item_id, sequence="MKV", seq_type=SeqType.PROTEIN, label=label, prediction=0.9
    )


def _edge(eval_id: str, score: float) -> ContaminationEdge:
    return ContaminationEdge(
        eval_id=eval_id,
        ref_id=f"r_{eval_id}",
        score=score,
        kind=DetectorKind.SEQUENCE,
        detector_id="d",
    )


def test_identity_axis_matches_hand_values_from_the_graph() -> None:
    items = (_eval("a"), _eval("b"), _eval("c"))
    graph = ContaminationGraph(edges=(_edge("a", 0.42), _edge("b", 0.80)))
    axis = identity_to_nearest_reference(items, graph)
    assert axis == {"a": 0.42, "b": 0.80, "c": 0.0}


def test_identity_axis_takes_the_maximum_edge_per_eval_item() -> None:
    # "nearest" reference = highest-scoring edge for that eval item.
    items = (_eval("a"),)
    graph = ContaminationGraph(edges=(_edge("a", 0.30), _edge("a", 0.75), _edge("a", 0.55)))
    assert identity_to_nearest_reference(items, graph) == {"a": 0.75}


def test_identity_axis_is_read_not_recomputed() -> None:
    # Sequences are identical (a recompute would give identity 1.0), but the edge
    # score is 0.42. The axis must trust the graph, returning 0.42 -- never 1.0.
    items = (_eval("a"),)
    graph = ContaminationGraph(edges=(_edge("a", 0.42),))
    assert identity_to_nearest_reference(items, graph)["a"] == 0.42


def test_items_with_no_edge_have_zero_identity() -> None:
    items = (_eval("clean"),)
    assert identity_to_nearest_reference(items, ContaminationGraph(edges=())) == {"clean": 0.0}


def test_label_class_axis_reads_labels() -> None:
    items = (_eval("a", label=0.0), _eval("b", label=1.0))
    assert label_class(items) == {"a": 0.0, "b": 1.0}
