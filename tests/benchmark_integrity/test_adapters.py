from __future__ import annotations

import sys
from types import ModuleType

import pytest
from pytest import MonkeyPatch

from veritas.benchmark_integrity.adapters import (
    HuggingFaceLocalAdapter,
    OpenAICompatibleAdapter,
    format_prompt,
    parse_answer,
)
from veritas.benchmark_integrity.contracts import (
    BenchmarkItem,
    Choice,
    ModelTarget,
    TaskType,
)
from veritas.benchmark_integrity.transforms import generate


class _Loader:
    @classmethod
    def from_pretrained(cls, model_id: str, **kwargs: object) -> object:
        return {"model_id": model_id, **kwargs}


def _multiple_choice() -> BenchmarkItem:
    return BenchmarkItem(
        id="q1",
        prompt="Pick one",
        expected_output="b",
        task_type=TaskType.MULTIPLE_CHOICE,
        choices=(Choice(id="a", text="wrong"), Choice(id="b", text="right")),
    )


def test_local_huggingface_adapter_loads_pinned_target_without_core_dependency(
    monkeypatch: MonkeyPatch,
) -> None:
    module = ModuleType("transformers")
    module.AutoTokenizer = _Loader  # type: ignore[attr-defined]
    module.AutoModelForCausalLM = _Loader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "transformers", module)
    adapter = HuggingFaceLocalAdapter(
        ModelTarget(id="local/model", revision="abc123", adapter="huggingface_local")
    )
    assert adapter.capabilities().token_probabilities is True


def test_multiple_choice_prompt_parser_and_label_remap() -> None:
    item = _multiple_choice()
    assert "a. wrong" in format_prompt(item)
    assert parse_answer(item, "B") == "b"
    derived = generate((item,), "choice_label_remap", 1, 42)[0]
    assert derived.item.expected_output == "option_2"
    assert derived.transformation.validation.value == "valid"


@pytest.mark.parametrize(
    "endpoint",
    (
        "file:///tmp/provider",
        "https://user:password@example.com/v1",
        "https://example.com/v1?redirect=http://localhost",
        "not-a-url",
    ),
)
def test_openai_compatible_adapter_rejects_unsafe_endpoint(endpoint: str) -> None:
    target = ModelTarget(id="model", adapter="openai_compatible", endpoint=endpoint)
    with pytest.raises(ValueError):
        OpenAICompatibleAdapter(target)


def test_openai_compatible_adapter_accepts_local_http_runtime() -> None:
    target = ModelTarget(
        id="model",
        adapter="openai_compatible",
        endpoint="http://127.0.0.1:8000/v1",
    )
    assert OpenAICompatibleAdapter(target).adapter_id == "openai_compatible"
