"""Benchmark, SplitSpec, MetricSpec: composition and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veritas.contracts import (
    Benchmark,
    EvalItem,
    MetricName,
    MetricSpec,
    SeqType,
    SplitSpec,
)


def _item(item_id: str) -> EvalItem:
    return EvalItem(id=item_id, sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.5)


def test_valid_benchmark() -> None:
    bench = Benchmark(
        name="demo",
        eval_items=(_item("e1"), _item("e2")),
        split=SplitSpec(name="random", kind="random"),
        metric=MetricSpec(name=MetricName.AUROC),
    )
    assert len(bench.eval_items) == 2
    assert bench.metric.name is MetricName.AUROC


def test_rejects_empty_eval_items() -> None:
    with pytest.raises(ValidationError):
        Benchmark(
            name="d",
            eval_items=(),
            split=SplitSpec(name="r", kind="random"),
            metric=MetricSpec(name=MetricName.AUROC),
        )


def test_rejects_duplicate_eval_item_ids() -> None:
    with pytest.raises(ValidationError):
        Benchmark(
            name="d",
            eval_items=(_item("e1"), _item("e1")),
            split=SplitSpec(name="r", kind="random"),
            metric=MetricSpec(name=MetricName.AUROC),
        )


def test_metric_spec_defaults() -> None:
    spec = MetricSpec(name=MetricName.SPEARMAN)
    assert spec.threshold is None
    assert spec.greater_is_better is True


def test_split_spec_fields() -> None:
    spec = SplitSpec(name="hom", kind="homology", description="grouped at 30% id")
    assert spec.kind == "homology"
    assert spec.description == "grouped at 30% id"


def test_round_trip_json() -> None:
    bench = Benchmark(
        name="demo",
        eval_items=(_item("e1"),),
        split=SplitSpec(name="r", kind="random"),
        metric=MetricSpec(name=MetricName.AUROC),
    )
    assert Benchmark.model_validate_json(bench.model_dump_json()) == bench
