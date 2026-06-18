"""Content-hash keyed cache of (expensive) detector search results."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from veritas.contracts import (
    ContaminationGraph,
    DetectorConfig,
    EvalItem,
    ReferenceItem,
)
from veritas.provenance import content_hash


class SearchCache:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._root / f"{key}.json"

    def get_or_compute(
        self, key: str, compute: Callable[[], ContaminationGraph]
    ) -> ContaminationGraph:
        path = self._path(key)
        if path.exists():
            return ContaminationGraph.model_validate_json(path.read_text())
        graph = compute()
        path.write_text(graph.model_dump_json())
        return graph


def cache_key(
    detector_id: str,
    config: DetectorConfig,
    eval_items: Sequence[EvalItem],
    reference_items: Sequence[ReferenceItem],
) -> str:
    payload = {
        "detector_id": detector_id,
        "config": config.model_dump(mode="json"),
        "eval": [{"id": e.id, "sequence": e.sequence} for e in eval_items],
        "reference": [{"id": r.id, "sequence": r.sequence} for r in reference_items],
    }
    return content_hash(payload)
