"""Built-in benchmark catalog and lazy Hugging Face dataset adapter."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from itertools import islice
from typing import Any

from veritas.benchmark_integrity.contracts import (
    Benchmark,
    BenchmarkItem,
    Choice,
    ScoringSpec,
    SourceRecord,
    TaskType,
    Visibility,
)

Row = Mapping[str, Any]
Converter = Callable[[Row, int, "CatalogEntry"], BenchmarkItem]


@dataclass(frozen=True)
class CatalogEntry:
    name: str
    description: str
    dataset_path: str
    dataset_config: str | None
    split: str
    task_type: TaskType
    license: str | None
    visibility: Visibility = Visibility.PUBLIC
    requires_auth: bool = False
    evaluator: str = "exact_match"
    approximate_items: int | None = None
    converter: str = "standard_mcq"

    def public_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["task_type"] = self.task_type.value
        value["visibility"] = self.visibility.value
        return value


_ENTRIES = (
    CatalogEntry(
        "mmlu",
        "57-subject multitask knowledge benchmark",
        "cais/mmlu",
        "all",
        "test",
        TaskType.MULTIPLE_CHOICE,
        "MIT",
        approximate_items=14042,
    ),
    CatalogEntry(
        "mmlu_pro",
        "Higher-difficulty MMLU revision with ten options",
        "TIGER-Lab/MMLU-Pro",
        None,
        "test",
        TaskType.MULTIPLE_CHOICE,
        "MIT",
        approximate_items=12032,
        converter="mmlu_pro",
    ),
    CatalogEntry(
        "arc_challenge",
        "AI2 science questions, Challenge split",
        "allenai/ai2_arc",
        "ARC-Challenge",
        "test",
        TaskType.MULTIPLE_CHOICE,
        "CC-BY-SA-4.0",
        approximate_items=1172,
        converter="labeled_choices",
    ),
    CatalogEntry(
        "openbookqa",
        "Open-book elementary science questions",
        "allenai/openbookqa",
        "main",
        "test",
        TaskType.MULTIPLE_CHOICE,
        "Apache-2.0",
        approximate_items=500,
        converter="labeled_choices",
    ),
    CatalogEntry(
        "hellaswag",
        "Commonsense sentence-completion benchmark",
        "Rowan/hellaswag",
        None,
        "validation",
        TaskType.MULTIPLE_CHOICE,
        "MIT",
        approximate_items=10042,
        converter="hellaswag",
    ),
    CatalogEntry(
        "commonsense_qa",
        "Commonsense multiple-choice questions",
        "tau/commonsense_qa",
        None,
        "validation",
        TaskType.MULTIPLE_CHOICE,
        None,
        approximate_items=1221,
        converter="labeled_choices",
    ),
    CatalogEntry(
        "piqa",
        "Physical interaction question answering",
        "ybisk/piqa",
        None,
        "validation",
        TaskType.MULTIPLE_CHOICE,
        "AFL-3.0",
        approximate_items=1838,
        converter="piqa",
    ),
    CatalogEntry(
        "winogrande",
        "Winograd-style commonsense reasoning",
        "allenai/winogrande",
        "winogrande_xl",
        "validation",
        TaskType.MULTIPLE_CHOICE,
        "Apache-2.0",
        approximate_items=1267,
        converter="winogrande",
    ),
    CatalogEntry(
        "truthfulqa",
        "Truthfulness under misconception controls",
        "truthfulqa/truthful_qa",
        "multiple_choice",
        "validation",
        TaskType.MULTIPLE_CHOICE,
        "Apache-2.0",
        approximate_items=817,
        converter="truthfulqa",
    ),
    CatalogEntry(
        "boolq",
        "Boolean question answering over passages",
        "google/boolq",
        None,
        "validation",
        TaskType.MULTIPLE_CHOICE,
        "CC-BY-SA-3.0",
        approximate_items=3270,
        converter="boolq",
    ),
    CatalogEntry(
        "gpqa",
        "Graduate-level, expert-authored science questions",
        "Idavidrein/gpqa",
        "gpqa_main",
        "train",
        TaskType.MULTIPLE_CHOICE,
        "CC-BY-4.0",
        visibility=Visibility.PRIVATE,
        requires_auth=True,
        approximate_items=448,
        converter="gpqa",
    ),
    CatalogEntry(
        "humaneval",
        "Python function synthesis",
        "openai/openai_humaneval",
        None,
        "test",
        TaskType.CODE,
        "MIT",
        evaluator="external_code_grader_required",
        approximate_items=164,
        converter="humaneval",
    ),
    CatalogEntry(
        "swe_bench_verified",
        "Repository-level issue resolution, verified subset",
        "princeton-nlp/SWE-bench_Verified",
        None,
        "test",
        TaskType.CODE,
        "MIT",
        evaluator="external_swebench_harness_required",
        approximate_items=500,
        converter="swe_bench",
    ),
)

CATALOG: dict[str, CatalogEntry] = {entry.name: entry for entry in _ENTRIES}

# Immutable upstream revisions captured for the v0.1.0 catalog. Users may override a
# revision explicitly, but a mutable branch is never the default for executable data.
_PINNED_REVISIONS = {
    "mmlu": "c30699e8356da336a370243923dbaf21066bb9fe",
    "mmlu_pro": "b189ec765aa7ed75c8acfea42df31fdae71f97be",
    "arc_challenge": "210d026faf9955653af8916fad021475a3f00453",
    "openbookqa": "388097ea7776314e93a529163e0fea805b8a6454",
    "hellaswag": "218ec52e09a7e7462a5400043bb9a69a41d06b76",
    "commonsense_qa": "94630fe30dad47192a8546eb75f094926d47e155",
    "piqa": "2e8ac2dffd59bac8c3c6714948f4c551a0848bb0",
    "winogrande": "01e74176c63542e6b0bcb004dcdea22d94fb67b5",
    "truthfulqa": "741b8276f2d1982aa3d5b832d3ee81ed3b896490",
    "boolq": "35b264d03638db9f4ce671b711558bf7ff0f80d5",
    "gpqa": "633f5ee89ab8ad4522a9f850766b73f62147ffdd",
    "humaneval": "7dce6050a7d6d172f3cc5c32aa97f52fa1a2e544",
    "swe_bench_verified": "c104f840cc67f8b6eec6f759ebc8b2693d585d4a",
}


def list_benchmarks() -> tuple[dict[str, object], ...]:
    """Return stable, serializable catalog metadata without downloading datasets."""
    return tuple(
        {**entry.public_dict(), "revision": _PINNED_REVISIONS[entry.name]} for entry in _ENTRIES
    )


class CatalogBenchmarkAdapter:
    """Load a named catalog entry through the optional ``datasets`` package."""

    adapter_id = "catalog"

    def load(self, config: Mapping[str, object]) -> Benchmark:
        name = str(config.get("name", ""))
        try:
            entry = CATALOG[name]
        except KeyError as exc:
            available = ", ".join(CATALOG)
            raise ValueError(f"unknown benchmark {name!r}; available: {available}") from exc
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise RuntimeError(
                "catalog benchmarks require the 'benchmarks' extra: "
                "pip install -e '.[cli,benchmarks]'"
            ) from exc

        split = str(config.get("split", entry.split))
        dataset_config = config.get("dataset_config", entry.dataset_config)
        revision = str(config.get("revision") or _PINNED_REVISIONS[entry.name])
        streaming = bool(config.get("streaming", True))
        loaded = load_dataset(
            entry.dataset_path,
            str(dataset_config) if dataset_config is not None else None,
            split=split,
            streaming=streaming,
            revision=revision,
        )
        offset = _integer(config.get("offset", 0))
        limit_value = config.get("limit")
        limit = _integer(limit_value) if limit_value is not None else None
        rows: Iterable[Row] = loaded
        selected = islice(rows, offset, None if limit is None else offset + limit)
        converter = _CONVERTERS[entry.converter]
        items = tuple(converter(row, offset + index, entry) for index, row in enumerate(selected))
        if not items:
            raise ValueError(f"catalog benchmark {name!r} produced no items")
        visibility = Visibility(str(config.get("visibility", entry.visibility.value)))
        return Benchmark(
            id=str(config.get("id", entry.name)),
            version=str(config.get("version", revision)),
            items=items,
            task_type=entry.task_type,
            visibility=visibility,
            split=split,
            scoring=ScoringSpec(kind=entry.evaluator),
            source=_source(entry),
            canonicalization={
                "catalog_name": entry.name,
                "dataset_config": dataset_config,
                "revision": revision,
                "offset": offset,
                "limit": limit,
            },
        )


def _metadata(row: Row, entry: CatalogEntry) -> dict[str, object]:
    keys = ("subject", "category", "topic", "repo", "base_commit")
    return {
        "catalog_name": entry.name,
        **{key: row[key] for key in keys if key in row},
    }


def _id(row: Row, index: int, entry: CatalogEntry) -> str:
    for key in ("id", "question_id", "instance_id", "task_id"):
        if row.get(key) not in (None, ""):
            return str(row[key])
    return f"{entry.name}:{index}"


def _integer(value: object) -> int:
    return int(str(value))


def _choice_id(index: int) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    return alphabet[index] if index < len(alphabet) else f"option_{index + 1}"


def _answer_id(value: object, choices: Sequence[Choice]) -> str:
    normalized = str(value).strip().lower()
    for choice in choices:
        if choice.id.lower() == normalized:
            return choice.id
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        number = int(value)
        if 0 <= number < len(choices):
            return choices[number].id
    raise ValueError(f"answer {value!r} does not identify a declared choice")


def _standard_mcq(row: Row, index: int, entry: CatalogEntry) -> BenchmarkItem:
    values = row.get("choices", row.get("options"))
    if not isinstance(values, Sequence) or isinstance(values, str | bytes):
        raise ValueError(f"{entry.name} row has no choice sequence")
    choices = tuple(Choice(id=_choice_id(i), text=str(value)) for i, value in enumerate(values))
    answer = row.get("answer", row.get("answer_index"))
    return BenchmarkItem(
        id=_id(row, index, entry),
        prompt=str(row["question"]),
        expected_output=_answer_id(answer, choices),
        task_type=entry.task_type,
        choices=choices,
        metadata=_metadata(row, entry),
        source=_source(entry),
    )


def _mmlu_pro(row: Row, index: int, entry: CatalogEntry) -> BenchmarkItem:
    return _standard_mcq(row, index, entry)


def _labeled_choices(row: Row, index: int, entry: CatalogEntry) -> BenchmarkItem:
    raw = row["choices"]
    if not isinstance(raw, Mapping):
        raise ValueError(f"{entry.name} choices must be a label/text mapping")
    labels = [str(value).lower() for value in raw["label"]]
    texts = [str(value) for value in raw["text"]]
    choices = tuple(Choice(id=label, text=text) for label, text in zip(labels, texts, strict=True))
    prompt = str(row.get("question", row.get("question_stem", "")))
    return BenchmarkItem(
        id=_id(row, index, entry),
        prompt=prompt,
        expected_output=_answer_id(row.get("answerKey", row.get("answer")), choices),
        task_type=entry.task_type,
        choices=choices,
        metadata=_metadata(row, entry),
        source=_source(entry),
    )


def _hellaswag(row: Row, index: int, entry: CatalogEntry) -> BenchmarkItem:
    choices = tuple(
        Choice(id=_choice_id(i), text=str(value)) for i, value in enumerate(row["endings"])
    )
    prompt = str(row.get("ctx", f"{row.get('ctx_a', '')} {row.get('ctx_b', '')}")).strip()
    return BenchmarkItem(
        id=_id(row, index, entry),
        prompt=prompt,
        expected_output=_answer_id(row["label"], choices),
        task_type=entry.task_type,
        choices=choices,
        metadata=_metadata(row, entry),
        source=_source(entry),
    )


def _piqa(row: Row, index: int, entry: CatalogEntry) -> BenchmarkItem:
    choices = (Choice(id="a", text=str(row["sol1"])), Choice(id="b", text=str(row["sol2"])))
    return BenchmarkItem(
        id=_id(row, index, entry),
        prompt=str(row["goal"]),
        expected_output=_answer_id(row["label"], choices),
        task_type=entry.task_type,
        choices=choices,
        metadata=_metadata(row, entry),
        source=_source(entry),
    )


def _winogrande(row: Row, index: int, entry: CatalogEntry) -> BenchmarkItem:
    choices = (Choice(id="a", text=str(row["option1"])), Choice(id="b", text=str(row["option2"])))
    answer = int(str(row["answer"])) - 1
    return BenchmarkItem(
        id=_id(row, index, entry),
        prompt=str(row["sentence"]),
        expected_output=_answer_id(answer, choices),
        task_type=entry.task_type,
        choices=choices,
        metadata=_metadata(row, entry),
        source=_source(entry),
    )


def _truthfulqa(row: Row, index: int, entry: CatalogEntry) -> BenchmarkItem:
    targets = row["mc1_targets"]
    if not isinstance(targets, Mapping):
        raise ValueError("truthfulqa mc1_targets must be an object")
    values = list(targets["choices"])
    labels = list(targets["labels"])
    choices = tuple(Choice(id=_choice_id(i), text=str(value)) for i, value in enumerate(values))
    correct = next(i for i, value in enumerate(labels) if int(value) == 1)
    return BenchmarkItem(
        id=_id(row, index, entry),
        prompt=str(row["question"]),
        expected_output=_answer_id(correct, choices),
        task_type=entry.task_type,
        choices=choices,
        metadata=_metadata(row, entry),
        source=_source(entry),
    )


def _boolq(row: Row, index: int, entry: CatalogEntry) -> BenchmarkItem:
    choices = (Choice(id="a", text="No"), Choice(id="b", text="Yes"))
    prompt = f"{row['passage']}\n\nQuestion: {row['question']}"
    return BenchmarkItem(
        id=_id(row, index, entry),
        prompt=prompt,
        expected_output="b" if bool(row["answer"]) else "a",
        task_type=entry.task_type,
        choices=choices,
        metadata=_metadata(row, entry),
        source=_source(entry),
    )


def _gpqa(row: Row, index: int, entry: CatalogEntry) -> BenchmarkItem:
    answers = [
        str(row["Correct Answer"]),
        *(str(row[f"Incorrect Answer {i}"]) for i in range(1, 4)),
    ]
    digest = hashlib.sha256(str(row["Question"]).encode()).digest()
    order = sorted(range(4), key=lambda value: digest[value])
    choices = tuple(
        Choice(id=_choice_id(i), text=answers[source]) for i, source in enumerate(order)
    )
    correct = order.index(0)
    return BenchmarkItem(
        id=_id(row, index, entry),
        prompt=str(row["Question"]),
        expected_output=_answer_id(correct, choices),
        task_type=entry.task_type,
        choices=choices,
        metadata=_metadata(row, entry),
        source=_source(entry),
    )


def _humaneval(row: Row, index: int, entry: CatalogEntry) -> BenchmarkItem:
    return BenchmarkItem(
        id=_id(row, index, entry),
        prompt=str(row["prompt"]),
        expected_output=str(row["canonical_solution"]),
        task_type=entry.task_type,
        metadata=_metadata(row, entry),
        source=_source(entry),
    )


def _swe_bench(row: Row, index: int, entry: CatalogEntry) -> BenchmarkItem:
    prompt = (
        f"Repository: {row['repo']}\n"
        f"Base commit: {row['base_commit']}\n\n"
        f"{row['problem_statement']}"
    )
    return BenchmarkItem(
        id=_id(row, index, entry),
        prompt=prompt,
        expected_output=str(row.get("patch", "")),
        task_type=entry.task_type,
        metadata=_metadata(row, entry),
        source=_source(entry),
        attachments=(str(row["repo"]), str(row["base_commit"])),
    )


def _source(entry: CatalogEntry) -> SourceRecord:
    return SourceRecord.model_validate(
        {
            "name": entry.dataset_path,
            "uri": f"https://huggingface.co/datasets/{entry.dataset_path}",
            "license": entry.license,
        }
    )


_CONVERTERS: dict[str, Converter] = {
    "standard_mcq": _standard_mcq,
    "mmlu_pro": _mmlu_pro,
    "labeled_choices": _labeled_choices,
    "hellaswag": _hellaswag,
    "piqa": _piqa,
    "winogrande": _winogrande,
    "truthfulqa": _truthfulqa,
    "boolq": _boolq,
    "gpqa": _gpqa,
    "humaneval": _humaneval,
    "swe_bench": _swe_bench,
}
