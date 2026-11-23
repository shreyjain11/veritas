"""Content-addressed response cache for resumable model evaluation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

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
# Transport settings change how a request is delivered, never what the model is asked.
_TRANSPORT_EXTRA = frozenset(
    {"api_key_env", "max_retries", "timeout_s", "retry_backoff_s", "concurrency"}
)
_BATCH = 32


def _generation_key(generation: dict[str, Any]) -> dict[str, Any]:
    extra = generation.get("extra")
    if not isinstance(extra, dict):
        return generation
    kept = {key: value for key, value in extra.items() if key not in _TRANSPORT_EXTRA}
    return {**generation, "extra": kept}


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
        paths = [self._path(item, config) for item in items]
        responses: list[ModelResponse | None] = [self._read(path) for path in paths]
        missing = [index for index, cached in enumerate(responses) if cached is None]
        self.hits += len(items) - len(missing)
        self.misses += len(missing)
        # Misses go to the adapter in batches so it can parallelize them, and each batch is
        # written before the next starts so an interrupted run loses at most one batch.
        for start in range(0, len(missing), _BATCH):
            batch = missing[start : start + _BATCH]
            generated = self._inner.generate([items[index] for index in batch], config)
            for index, response in zip(batch, generated, strict=True):
                if response.error is None:
                    path = paths[index]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = path.with_suffix(".tmp")
                    temporary.write_text(response.model_dump_json(), encoding="utf-8")
                    temporary.replace(path)
                responses[index] = response
        return [response for response in responses if response is not None]

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
        target["generation"] = _generation_key(target["generation"])
        payload = {
            "target": target,
            "adapter": self._inner.adapter_id,
            "item": item.model_dump(mode="json"),
            "generation": _generation_key(config.model_dump(mode="json")),
            "prompt_format": PROMPT_FORMAT_VERSION,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        return self._cache_dir / digest[:2] / f"{digest}.json"
