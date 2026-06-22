"""(a) Categorical (metadata-keyed) stratification axis + curve.

A ``metadata:<key>`` axis buckets eval items by a categorical ``EvalItem.metadata``
field (e.g. ProteinGym's MSA depth Low/Medium/High) -- one bucket per category,
carrying the category name as its label -- and honors the SAME small/empty-bucket
-> INSUFFICIENT_CLEAN_DATA guard as the equal-width path.
"""

from __future__ import annotations

import pytest

from tests.conftest import DEFAULT_SEED
from veritas.contracts import EvalItem, MetricName, MetricSpec, ResultStatus, SeqType
from veritas.stratify import StratifiedCurve, categorical_performance_curve, metadata_category

_ACCURACY = MetricSpec(name=MetricName.ACCURACY)


def _item(item_id: str, label: float, prediction: float, depth: str) -> EvalItem:
    return EvalItem(
        id=item_id,
        sequence="MKV",
        seq_type=SeqType.PROTEIN,
        label=label,
        prediction=prediction,
        metadata={"depth": depth},
    )


# --- axis ---


def test_metadata_category_reads_the_key() -> None:
    items = (_item("a", 1.0, 0.9, "Low"), _item("b", 1.0, 0.9, "High"))
    assert metadata_category(items, "depth") == {"a": "Low", "b": "High"}


def test_metadata_category_stringifies_non_string_values() -> None:
    items = (
        EvalItem(
            id="a",
            sequence="MKV",
            seq_type=SeqType.PROTEIN,
            label=1.0,
            prediction=0.9,
            metadata={"k": 3},
        ),
    )
    assert metadata_category(items, "k") == {"a": "3"}


def test_metadata_category_rejects_a_missing_key() -> None:
    items = (_item("a", 1.0, 0.9, "Low"),)
    with pytest.raises(ValueError, match="metadata key"):
        metadata_category(items, "absent")


# --- curve ---


def _curve(
    items: tuple[EvalItem, ...],
    *,
    categories: tuple[str, ...] | None = None,
    min_bucket_n: int = 2,
) -> StratifiedCurve:
    axis = metadata_category(items, "depth")
    return categorical_performance_curve(
        items,
        axis,
        _ACCURACY,
        axis_name="metadata:depth",
        categories=categories,
        seed=DEFAULT_SEED,
        n_bootstrap=100,
        min_bucket_n=min_bucket_n,
    )


def test_one_bucket_per_category_carrying_the_category_label() -> None:
    items = (
        _item("a", 1.0, 0.9, "Low"),
        _item("b", 0.0, 0.1, "Low"),
        _item("c", 1.0, 0.9, "High"),
        _item("d", 0.0, 0.1, "High"),
    )
    curve = _curve(items)  # default order = sorted unique: High, Low
    assert curve.axis_name == "metadata:depth"
    assert [b.label for b in curve.buckets] == ["High", "Low"]
    assert [b.n for b in curve.buckets] == [2, 2]
    assert all(b.estimate.status is ResultStatus.OK for b in curve.buckets)


def test_explicit_category_order_is_honored() -> None:
    items = tuple(
        _item(f"x{i}", 1.0, 0.9, depth)
        for i, depth in enumerate(["Low", "Low", "Medium", "Medium", "High", "High"])
    )
    curve = _curve(items, categories=("Low", "Medium", "High"))
    assert [b.label for b in curve.buckets] == ["Low", "Medium", "High"]


def test_small_bucket_is_insufficient_clean_data() -> None:
    # 'Low' has a single item -> below min_bucket_n -> INSUFFICIENT (same guard as equal-width).
    items = (
        _item("a", 1.0, 0.9, "Low"),
        _item("b", 1.0, 0.9, "High"),
        _item("c", 0.0, 0.1, "High"),
    )
    curve = _curve(items, min_bucket_n=2)
    by_label = {b.label: b for b in curve.buckets}
    assert by_label["Low"].n == 1
    assert by_label["Low"].estimate.value is None
    assert by_label["Low"].estimate.status is ResultStatus.INSUFFICIENT_CLEAN_DATA


def test_declared_but_absent_category_is_empty_and_insufficient() -> None:
    items = (_item("a", 1.0, 0.9, "Low"), _item("b", 0.0, 0.1, "Low"))
    curve = _curve(items, categories=("Low", "High"))
    by_label = {b.label: b for b in curve.buckets}
    assert by_label["High"].n == 0
    assert by_label["High"].estimate.status is ResultStatus.INSUFFICIENT_CLEAN_DATA


def test_category_outside_a_declared_order_is_rejected() -> None:
    items = (_item("a", 1.0, 0.9, "Mystery"),)
    axis = metadata_category(items, "depth")
    with pytest.raises(ValueError, match="not in declared categories"):
        categorical_performance_curve(
            items,
            axis,
            _ACCURACY,
            axis_name="metadata:depth",
            categories=("Low", "High"),
            seed=DEFAULT_SEED,
            n_bootstrap=10,
        )


def test_curve_is_deterministic_given_seed() -> None:
    items = (
        _item("a", 1.0, 0.9, "Low"),
        _item("b", 0.0, 0.1, "Low"),
        _item("c", 1.0, 0.9, "High"),
        _item("d", 0.0, 0.1, "High"),
    )
    assert _curve(items) == _curve(items)


def test_missing_prediction_is_rejected() -> None:
    items = (
        EvalItem(
            id="x", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, metadata={"depth": "Low"}
        ),
    )
    with pytest.raises(ValueError, match="prediction"):
        categorical_performance_curve(
            items,
            {"x": "Low"},
            _ACCURACY,
            axis_name="metadata:depth",
            seed=DEFAULT_SEED,
            n_bootstrap=10,
        )
