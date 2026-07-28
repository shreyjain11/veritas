from __future__ import annotations

from pathlib import Path

from veritas.benchmark_integrity.adapters import ReplayAdapter
from veritas.benchmark_integrity.cache import CachedAdapter
from veritas.benchmark_integrity.contracts import (
    BenchmarkItem,
    GenerationConfig,
    ModelTarget,
    TaskType,
)


class CountingReplay(ReplayAdapter):
    calls = 0

    def generate(self, items, config):  # type: ignore[no-untyped-def]
        self.calls += 1
        return super().generate(items, config)


def test_content_addressed_cache_reuses_exact_request(tmp_path: Path) -> None:
    item = BenchmarkItem(
        id="q1", prompt="question", expected_output="answer", task_type=TaskType.OPEN_ENDED
    )
    inner = CountingReplay({"q1": "answer"})
    adapter = CachedAdapter(
        inner,
        ModelTarget(id="fixture", adapter="replay"),
        tmp_path,
    )
    config = GenerationConfig(seed=42)
    assert adapter.generate((item,), config)[0].parsed_answer == "answer"
    assert adapter.generate((item,), config)[0].parsed_answer == "answer"
    assert inner.calls == 1
    assert len(list(tmp_path.rglob("*.json"))) == 1
