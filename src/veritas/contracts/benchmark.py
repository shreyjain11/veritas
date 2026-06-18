"""Benchmark and its split/metric declarations."""

from __future__ import annotations

from pydantic import Field, field_validator

from veritas.contracts.base import FrozenModel
from veritas.contracts.enums import MetricName
from veritas.contracts.eval_item import EvalItem


class SplitSpec(FrozenModel):
    name: str
    kind: str
    description: str = ""


class MetricSpec(FrozenModel):
    name: MetricName
    threshold: float | None = None
    greater_is_better: bool = True


class Benchmark(FrozenModel):
    name: str
    eval_items: tuple[EvalItem, ...] = Field(min_length=1)
    split: SplitSpec
    metric: MetricSpec

    @field_validator("eval_items")
    @classmethod
    def _ids_unique(cls, value: tuple[EvalItem, ...]) -> tuple[EvalItem, ...]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("Benchmark contains duplicate eval item ids")
        return value
