"""Pluggable adapter Protocols — the only place model/benchmark specifics may live.

Core logic depends on these abstractions, never on a concrete model, benchmark,
or organism (CLAUDE.md first principle #5).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from veritas.contracts import Benchmark, ReferenceItem


@runtime_checkable
class BenchmarkAdapter(Protocol):
    def load_benchmark(self) -> Benchmark: ...


@runtime_checkable
class ReferenceAdapter(Protocol):
    def load_reference(self) -> tuple[ReferenceItem, ...]: ...


@runtime_checkable
class ModelAdapter(Protocol):
    def load_predictions(self) -> dict[str, float]: ...
