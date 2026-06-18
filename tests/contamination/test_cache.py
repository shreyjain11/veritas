"""Content-hash search cache: compute once, reuse on hit, persist across instances."""

from __future__ import annotations

from pathlib import Path

from veritas.contamination.cache import SearchCache, cache_key
from veritas.contracts import (
    ContaminationEdge,
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    ReferenceItem,
    SeqType,
)


def _graph() -> ContaminationGraph:
    return ContaminationGraph(
        edges=(
            ContaminationEdge(
                eval_id="e1", ref_id="r1", score=1.0, kind=DetectorKind.SEQUENCE, detector_id="m"
            ),
        )
    )


def test_miss_computes_then_hit_reuses(tmp_path: Path) -> None:
    cache = SearchCache(tmp_path)
    calls = {"n": 0}

    def compute() -> ContaminationGraph:
        calls["n"] += 1
        return _graph()

    first = cache.get_or_compute("k1", compute)
    second = cache.get_or_compute("k1", compute)
    assert calls["n"] == 1  # second call served from cache
    assert first == second == _graph()


def test_distinct_keys_recompute(tmp_path: Path) -> None:
    cache = SearchCache(tmp_path)
    calls = {"n": 0}

    def compute() -> ContaminationGraph:
        calls["n"] += 1
        return _graph()

    cache.get_or_compute("k1", compute)
    cache.get_or_compute("k2", compute)
    assert calls["n"] == 2


def test_cache_persists_across_instances(tmp_path: Path) -> None:
    def compute() -> ContaminationGraph:
        raise AssertionError("should not be called on a warm cache")

    SearchCache(tmp_path).get_or_compute("k1", _graph)
    assert SearchCache(tmp_path).get_or_compute("k1", compute) == _graph()


def test_cache_key_changes_with_config(tmp_path: Path) -> None:
    evals = (EvalItem(id="e1", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0),)
    refs = (ReferenceItem(id="r1", sequence="MKV", seq_type=SeqType.PROTEIN),)
    config_a = DetectorConfig(
        kind=DetectorKind.SEQUENCE, name="mmseqs", identity_threshold=0.3, coverage_threshold=0.5
    )
    config_b = DetectorConfig(
        kind=DetectorKind.SEQUENCE, name="mmseqs", identity_threshold=0.9, coverage_threshold=0.5
    )
    assert cache_key("mmseqs", config_a, evals, refs) != cache_key("mmseqs", config_b, evals, refs)
