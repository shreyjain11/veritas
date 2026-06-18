"""Property-based invariants for metrics and de-leak (Hypothesis)."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st
from numpy.typing import NDArray

from veritas.contracts import (
    ContaminationEdge,
    ContaminationGraph,
    DetectorKind,
    EvalItem,
    MetricName,
    SeqType,
)
from veritas.metrics import compute_metric, drop


def _items(ids: tuple[str, ...]) -> tuple[EvalItem, ...]:
    return tuple(
        EvalItem(id=i, sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.9)
        for i in ids
    )


def _graph(ids: tuple[str, ...]) -> ContaminationGraph:
    return ContaminationGraph(
        edges=tuple(
            ContaminationEdge(
                eval_id=i, ref_id="r", score=1.0, kind=DetectorKind.SEQUENCE, detector_id="t"
            )
            for i in ids
        )
    )


@st.composite
def _binary_dataset(draw: st.DrawFn) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    size = draw(st.integers(min_value=4, max_value=20))
    labels = draw(st.lists(st.sampled_from([0.0, 1.0]), min_size=size, max_size=size))
    assume(0.0 in labels and 1.0 in labels)
    # Integer-valued scores keep a monotone transform (exp) exactly rank-preserving
    # in floating point: distinct ints -> distinct exp, tied ints -> tied exp.
    scores = draw(st.lists(st.integers(min_value=-20, max_value=20), min_size=size, max_size=size))
    return np.array(labels, dtype=float), np.array(scores, dtype=float)


@st.composite
def _continuous_pair(draw: st.DrawFn) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    size = draw(st.integers(min_value=4, max_value=20))
    integers = st.integers(min_value=-20, max_value=20)
    labels = draw(st.lists(integers, min_size=size, max_size=size))
    scores = draw(st.lists(integers, min_size=size, max_size=size))
    assume(len(set(labels)) > 1 and len(set(scores)) > 1)
    return np.array(labels, dtype=float), np.array(scores, dtype=float)


@given(st.sets(st.sampled_from(["a", "b", "c", "d"])))
def test_drop_keeps_exactly_the_uncontaminated(contaminated: set[str]) -> None:
    # Equality, not subset+disjoint: the weaker assertions were passed by a drop that
    # removed everything (kept={}) or nothing. It must keep EXACTLY the clean items.
    all_ids = {"a", "b", "c", "d"}
    kept = drop(_items(("a", "b", "c", "d")), _graph(tuple(contaminated)))
    kept_ids = {item.id for item in kept}
    assert kept_ids == all_ids - contaminated


def test_drop_is_idempotent() -> None:
    items = _items(("a", "b", "c"))
    graph = _graph(("a",))
    once = drop(items, graph)
    assert drop(once, graph) == once


@example((np.array([0.0, 1.0, 0.0, 1.0]), np.array([5.0, 5.0, 5.0, 5.0])))  # pin: all-equal scores
@given(_binary_dataset())
def test_auroc_invariant_under_monotone_transform(
    data: tuple[NDArray[np.float64], NDArray[np.float64]],
) -> None:
    labels, scores = data
    assert compute_metric(MetricName.AUROC, labels, scores) == pytest.approx(
        compute_metric(MetricName.AUROC, labels, np.exp(scores))
    )


@given(_continuous_pair())
def test_spearman_invariant_under_monotone_transform(
    data: tuple[NDArray[np.float64], NDArray[np.float64]],
) -> None:
    labels, scores = data
    assert compute_metric(MetricName.SPEARMAN, labels, scores) == pytest.approx(
        compute_metric(MetricName.SPEARMAN, labels, np.exp(scores))
    )


def test_reweight_uniform_weights_equals_unweighted() -> None:
    labels = np.array([0.0, 1.0, 1.0, 0.0])
    scores = np.array([0.2, 0.8, 0.9, 0.1])
    assert compute_metric(
        MetricName.ACCURACY, labels, scores, threshold=0.5, weights=np.ones(4)
    ) == pytest.approx(compute_metric(MetricName.ACCURACY, labels, scores, threshold=0.5))


def test_reweight_zero_weight_equals_dropping_item() -> None:
    labels = np.array([0.0, 1.0, 1.0, 0.0])
    scores = np.array([0.2, 0.8, 0.9, 0.1])
    weighted = compute_metric(
        MetricName.ACCURACY, labels, scores, threshold=0.5, weights=np.array([0.0, 1.0, 1.0, 1.0])
    )
    dropped = compute_metric(MetricName.ACCURACY, labels[1:], scores[1:], threshold=0.5)
    assert weighted == pytest.approx(dropped)
