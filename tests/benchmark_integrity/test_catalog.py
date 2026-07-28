from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType

from pytest import MonkeyPatch
from typer.testing import CliRunner

from veritas.benchmark_integrity.catalog import CatalogBenchmarkAdapter, list_benchmarks
from veritas.benchmark_integrity.service import inspect_audit, load_spec
from veritas.cli.app import app


def _datasets_module(rows: list[dict[str, object]]) -> ModuleType:
    module = ModuleType("datasets")

    def load_dataset(path: str, name: str | None, **kwargs: object) -> object:
        assert path == "cais/mmlu"
        assert name == "all"
        assert kwargs["split"] == "test"
        assert kwargs["revision"] == "c30699e8356da336a370243923dbaf21066bb9fe"
        return rows

    module.load_dataset = load_dataset  # type: ignore[attr-defined]
    return module


def test_catalog_lists_frontier_benchmark_presets() -> None:
    rows = list_benchmarks()
    names = {str(row["name"]) for row in rows}
    assert {"mmlu", "gpqa", "humaneval", "swe_bench_verified"} <= names
    gpqa = next(row for row in rows if row["name"] == "gpqa")
    assert gpqa["requires_auth"] is True
    assert gpqa["visibility"] == "private"
    assert len(str(gpqa["revision"])) == 40


def test_catalog_adapter_normalizes_and_limits_mmlu(monkeypatch: MonkeyPatch) -> None:
    rows = [
        {
            "question": "2 + 2?",
            "choices": ["3", "4", "5", "6"],
            "answer": 1,
            "subject": "elementary_mathematics",
        },
        {
            "question": "Ignored by limit",
            "choices": ["a", "b", "c", "d"],
            "answer": 0,
        },
    ]
    monkeypatch.setitem(sys.modules, "datasets", _datasets_module(rows))
    benchmark = CatalogBenchmarkAdapter().load({"adapter": "catalog", "name": "mmlu", "limit": 1})
    assert benchmark.id == "mmlu"
    assert len(benchmark.items) == 1
    assert benchmark.items[0].expected_output == "b"
    assert benchmark.items[0].metadata["subject"] == "elementary_mathematics"


def test_numeric_choice_labels_are_not_mistaken_for_zero_based_indexes(
    monkeypatch: MonkeyPatch,
) -> None:
    module = ModuleType("datasets")
    module.load_dataset = lambda *args, **kwargs: [  # type: ignore[attr-defined]
        {
            "question": "Which label is correct?",
            "choices": {"label": ["1", "2"], "text": ["first", "second"]},
            "answerKey": "1",
        }
    ]
    monkeypatch.setitem(sys.modules, "datasets", module)
    benchmark = CatalogBenchmarkAdapter().load({"name": "arc_challenge", "limit": 1})
    assert benchmark.items[0].expected_output == "1"


def test_catalog_inspection_uses_limit_without_downloading(tmp_path: Path) -> None:
    spec = {
        "schema_version": "2.0",
        "benchmark": {"adapter": "catalog", "name": "mmlu", "limit": 25},
        "model": {"id": "model", "adapter": "replay", "generation": {"max_tokens": 4}},
        "transformations": [{"type": "choice_permutation", "variants_per_item": 2}],
    }
    path = tmp_path / "catalog-audit.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    assert inspect_audit(load_spec(path))["estimated_requests"] == 75


def test_benchmarks_cli_supports_text_and_json() -> None:
    runner = CliRunner()
    text_result = runner.invoke(app, ["benchmarks"])
    assert text_result.exit_code == 0
    assert "mmlu" in text_result.output
    json_result = runner.invoke(app, ["benchmarks", "gpqa"])
    assert json_result.exit_code == 0
    assert json.loads(json_result.output)["requires_auth"] is True
