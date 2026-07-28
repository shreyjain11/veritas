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


class CachedAdapter:
    adapter_id = "cached"

    def __init__(self, inner: ModelAdapter, target: ModelTarget, cache_dir: Path) -> None:
        self._inner = inner
        self._target = target
        self._cache_dir = cache_dir

    def capabilities(self) -> ModelCapabilities:
        return self._inner.capabilities()

    def generate(
        self, items: Sequence[BenchmarkItem], config: GenerationConfig
    ) -> Sequence[ModelResponse]:
        responses: list[ModelResponse] = []
        for item in items:
            path = self._path(item, config)
            if path.exists():
                responses.append(
                    ModelResponse.model_validate_json(path.read_text(encoding="utf-8"))
                )
                continue
            response = self._inner.generate((item,), config)[0]
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(response.model_dump_json(), encoding="utf-8")
            temporary.replace(path)
            responses.append(response)
        return responses

    def _path(self, item: BenchmarkItem, config: GenerationConfig) -> Path:
        payload = {
            "target": self._target.model_dump(mode="json"),
            "adapter": self._inner.adapter_id,
            "item": item.model_dump(mode="json"),
            "generation": config.model_dump(mode="json"),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        return self._cache_dir / digest[:2] / f"{digest}.json"
