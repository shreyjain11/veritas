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


def test_transport_settings_do_not_invalidate_the_cache(tmp_path: Path) -> None:
    items = tuple(
        BenchmarkItem(
            id=f"q{index}", prompt="question", expected_output="x", task_type=TaskType.OPEN_ENDED
        )
        for index in range(3)
    )
    inner = CountingReplay({item.id: "x" for item in items})
    target = ModelTarget(id="fixture", adapter="replay")
    first = CachedAdapter(inner, target, tmp_path)
    slow = GenerationConfig(extra={"concurrency": 1, "max_retries": 0, "top_p": 0.9})
    fast = GenerationConfig(extra={"concurrency": 16, "timeout_s": 5, "top_p": 0.9})
    assert [r.item_id for r in first.generate(items, slow)] == ["q0", "q1", "q2"]
    assert inner.calls == 1  # all three misses went to the adapter as one batch
    second = CachedAdapter(inner, target, tmp_path)
    second.generate(items, fast)
    assert (second.hits, second.misses, inner.calls) == (3, 0, 1)
    # A setting that reaches the provider is a different request.
    second.generate(items, GenerationConfig(extra={"top_p": 0.5}))
    assert second.misses == 3
