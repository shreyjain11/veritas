"""Content-addressed response cache for resumable model evaluation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from veritas.benchmark_integrity.adapters import ModelAdapter
from veritas.benchmark_integrity.contracts import (
    BenchmarkItem,
    GenerationConfig,
    ModelCapabilities,
    ModelResponse,
    ModelTarget,
)
from veritas.benchmark_integrity.prompting import PROMPT_FORMAT_VERSION

# Run budgets bound how many requests an audit may make; they never change a response,
# so raising a limit and resuming must reuse everything already paid for.
_BUDGET_FIELDS = frozenset({"request_limit", "token_limit", "max_cost_usd"})


class CachedAdapter:
    """Wrap an adapter so each exact request is generated at most once.

    Errored responses are returned but never written, so a resumed run retries them.
    """

    adapter_id = "cached"

    def __init__(self, inner: ModelAdapter, target: ModelTarget, cache_dir: Path) -> None:
        self._inner = inner
        self._target = target
        self._cache_dir = cache_dir
        self.hits = 0
        self.misses = 0

    def capabilities(self) -> ModelCapabilities:
        return self._inner.capabilities()

    def generate(
        self, items: Sequence[BenchmarkItem], config: GenerationConfig
    ) -> Sequence[ModelResponse]:
        responses: list[ModelResponse] = []
        for item in items:
            path = self._path(item, config)
            cached = self._read(path)
            if cached is not None:
                self.hits += 1
                responses.append(cached)
                continue
            self.misses += 1
            response = self._inner.generate((item,), config)[0]
            if response.error is None:
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(".tmp")
                temporary.write_text(response.model_dump_json(), encoding="utf-8")
                temporary.replace(path)
            responses.append(response)
        return responses

    @staticmethod
    def _read(path: Path) -> ModelResponse | None:
        if not path.exists():
            return None
        try:
            return ModelResponse.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            return None  # a truncated or foreign file is treated as a miss and rewritten

    def _path(self, item: BenchmarkItem, config: GenerationConfig) -> Path:
        target = {
            key: value
            for key, value in self._target.model_dump(mode="json").items()
            if key not in _BUDGET_FIELDS
        }
        payload = {
            "target": target,
            "adapter": self._inner.adapter_id,
            "item": item.model_dump(mode="json"),
            "generation": config.model_dump(mode="json"),
            "prompt_format": PROMPT_FORMAT_VERSION,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        return self._cache_dir / digest[:2] / f"{digest}.json"
