"""(f) Property-based stratification invariants (Hypothesis).

- every difficulty value maps to exactly one in-range bucket (assign total + valid);
- buckets partition the eval set exactly (counts sum to N, nothing dropped/double-counted);
- performance constructed monotone in the difficulty axis is recovered monotone.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.conftest import DEFAULT_SEED
from veritas.contracts import (
    ContaminationEdge,
    ContaminationGraph,
    DetectorKind,
    EvalItem,
    MetricName,
    MetricSpec,
    SeqType,
)
from veritas.stratify import (
    fixed_bins,
    identity_to_nearest_reference,
    performance_curve,
)

_FINITE = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_ACCURACY = MetricSpec(name=MetricName.ACCURACY)


def _eval(item_id: str, prediction: float) -> EvalItem:
    return EvalItem(
        id=item_id, sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=prediction
    )


@given(st.floats(allow_nan=False, allow_infinity=False), st.integers(min_value=1, max_value=8))
def test_assign_is_always_a_valid_single_bucket(value: float, n_bins: int) -> None:
    index = fixed_bins(n_bins, lo=0.0, hi=1.0).assign(value)
    assert 0 <= index < n_bins


@st.composite
def _items_and_axis(draw: st.DrawFn) -> tuple[tuple[EvalItem, ...], dict[str, float]]:
    n = draw(st.integers(min_value=2, max_value=30))
    predictions = draw(st.lists(_FINITE, min_size=n, max_size=n))
    values = draw(st.lists(_FINITE, min_size=n, max_size=n))
    items = tuple(_eval(f"i{j}", predictions[j]) for j in range(n))
    axis = {f"i{j}": values[j] for j in range(n)}
    return items, axis


@given(_items_and_axis(), st.integers(min_value=1, max_value=6))
def test_buckets_partition_eval_set_exactly(
    items_axis: tuple[tuple[EvalItem, ...], dict[str, float]], n_bins: int
) -> None:
    items, axis = items_axis
    bins = fixed_bins(n_bins, lo=0.0, hi=1.0)
    curve = performance_curve(items, axis, bins, _ACCURACY, seed=DEFAULT_SEED, n_bootstrap=1)
    assert len(curve.buckets) == n_bins
    assert sum(b.n for b in curve.buckets) == len(items)  # no item dropped or double-counted


@settings(max_examples=50, deadline=None)
@given(st.lists(st.integers(min_value=0, max_value=10), min_size=4, max_size=4))
def test_monotone_performance_yields_monotone_curve(correct_counts: list[int]) -> None:
    counts = sorted(correct_counts)  # non-decreasing accuracy planted across buckets
    items: list[EvalItem] = []
    edges: list[ContaminationEdge] = []
    for bucket, n_correct in enumerate(counts):
        identity = bucket * 0.25 + 0.05  # lands squarely in bucket `bucket` of fixed_bins(4)
        for j in range(10):
            item_id = f"b{bucket}_{j}"
            items.append(_eval(item_id, 0.9 if j < n_correct else 0.1))
            edges.append(
                ContaminationEdge(
                    eval_id=item_id,
                    ref_id="r",
                    score=identity,
                    kind=DetectorKind.SEQUENCE,
                    detector_id="d",
                )
            )
    graph = ContaminationGraph(edges=tuple(edges))
    axis = identity_to_nearest_reference(tuple(items), graph)
    curve = performance_curve(
        tuple(items),
        axis,
        fixed_bins(4, lo=0.0, hi=1.0),
        _ACCURACY,
        seed=DEFAULT_SEED,
        n_bootstrap=50,
    )
    values = [b.estimate.value for b in curve.buckets]
    assert all(v is not None for v in values)
    assert all(values[i] <= values[i + 1] + 1e-9 for i in range(3))  # type: ignore[operator]
