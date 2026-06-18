"""Adapter Protocols: the only place model/benchmark specifics may live (principle #5).

Verifies the Protocols are runtime-checkable and that a conforming fake adapter
produces valid core contracts.
"""

from __future__ import annotations

from veritas.contracts import (
    Benchmark,
    EvalItem,
    MetricName,
    MetricSpec,
    ReferenceItem,
    SeqType,
    SplitSpec,
)
from veritas.io import BenchmarkAdapter, ModelAdapter, ReferenceAdapter


class _FakeBenchmark:
    def load_benchmark(self) -> Benchmark:
        return Benchmark(
            name="fake",
            eval_items=(
                EvalItem(
                    id="e1", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.5
                ),
            ),
            split=SplitSpec(name="r", kind="random"),
            metric=MetricSpec(name=MetricName.AUROC),
        )


class _FakeReference:
    def load_reference(self) -> tuple[ReferenceItem, ...]:
        return (ReferenceItem(id="r1", sequence="MKV", seq_type=SeqType.PROTEIN),)


class _FakeModel:
    def load_predictions(self) -> dict[str, float]:
        return {"e1": 0.5}


def test_fake_benchmark_adapter_produces_valid_benchmark() -> None:
    adapter: BenchmarkAdapter = _FakeBenchmark()
    assert isinstance(adapter.load_benchmark(), Benchmark)


def test_benchmark_adapter_is_runtime_checkable() -> None:
    assert isinstance(_FakeBenchmark(), BenchmarkAdapter)


def test_reference_adapter_is_runtime_checkable() -> None:
    assert isinstance(_FakeReference(), ReferenceAdapter)


def test_model_adapter_is_runtime_checkable() -> None:
    assert isinstance(_FakeModel(), ModelAdapter)
