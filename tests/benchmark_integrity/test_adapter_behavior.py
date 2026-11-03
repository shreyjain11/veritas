"""Hermetic behavior tests for the v2 model adapters and response cache (no network)."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from urllib.error import HTTPError, URLError

import pytest

from veritas.benchmark_integrity import adapters as adapters_module
from veritas.benchmark_integrity.adapters import (
    HuggingFaceLocalAdapter,
    OpenAICompatibleAdapter,
    ReplayAdapter,
)
from veritas.benchmark_integrity.cache import CachedAdapter
from veritas.benchmark_integrity.contracts import (
    BenchmarkItem,
    Choice,
    GenerationConfig,
    ModelCapabilities,
    ModelResponse,
    ModelTarget,
    TaskType,
)

ITEM = BenchmarkItem(
    id="q1",
    prompt="Pick one",
    expected_output="b",
    task_type=TaskType.MULTIPLE_CHOICE,
    choices=(Choice(id="a", text="wrong"), Choice(id="b", text="right")),
)


def _target(**extra: Any) -> ModelTarget:
    return ModelTarget(
        id="model-x",
        adapter="openai_compatible",
        endpoint="https://provider.example/v1/",
        system_prompt="Answer tersely.",
        generation=GenerationConfig(
            extra={"api_key_env": "TEST_KEY", "retry_backoff_s": 0, **extra}
        ),
    )


class _Body:
    def __init__(self, payload: object) -> None:
        self._data = json.dumps(payload).encode()

    def __enter__(self) -> _Body:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._data


def _http_error(code: int, body: str = "") -> HTTPError:
    return HTTPError("https://provider.example", code, "err", {}, io.BytesIO(body.encode()))  # type: ignore[arg-type]


def _install(monkeypatch: pytest.MonkeyPatch, outcomes: list[object]) -> list[dict[str, Any]]:
    """Patch urlopen to return/raise ``outcomes`` in order; record each request body."""
    sent: list[dict[str, Any]] = []

    def fake_urlopen(request: Any, timeout: float) -> _Body:
        sent.append({"body": json.loads(request.data), "headers": dict(request.headers)})
        outcome = outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return _Body(outcome)

    monkeypatch.setattr(adapters_module, "urlopen", fake_urlopen)
    monkeypatch.setenv("TEST_KEY", "sk-test")
    return sent


def _ok(content: object = "The answer is B", **extra: Any) -> dict[str, Any]:
    return {
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"total_tokens": 12},
        **extra,
    }


def test_payload_is_a_valid_chat_completion_request(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _install(monkeypatch, [_ok()])
    target = _target(top_p=0.5)
    adapter = OpenAICompatibleAdapter(target, "TEST_KEY")
    config = target.generation.model_copy(update={"max_tokens": 8})
    response = adapter.generate([ITEM], config)[0]
    body = sent[0]["body"]
    assert body["model"] == "model-x"
    assert body["messages"][0] == {"role": "system", "content": "Answer tersely."}
    assert "Choices:" in body["messages"][1]["content"]
    assert body["max_tokens"] == 8 and body["top_p"] == 0.5
    # Veritas' own settings never reach the provider; a null seed is omitted.
    assert not {"extra", "api_key_env", "retry_backoff_s", "seed"} & set(body)
    assert sent[0]["headers"]["Authorization"] == "Bearer sk-test"
    assert response.parsed_answer == "b"
    assert response.token_count == 12
    assert "sk-test" not in json.dumps(response.model_dump(mode="json"))


def test_transient_failures_are_retried_then_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, [_http_error(429), URLError("reset"), _ok()])
    adapter = OpenAICompatibleAdapter(_target(max_retries=3), "TEST_KEY")
    assert adapter.generate([ITEM], GenerationConfig())[0].attempt == 3

    _install(monkeypatch, [_http_error(503), _http_error(503)])
    adapter = OpenAICompatibleAdapter(_target(max_retries=1), "TEST_KEY")
    failed = adapter.generate([ITEM], GenerationConfig())[0]
    assert failed.error == "HTTP 503 after 2 attempt(s)"
    assert failed.parsed_answer is None


def test_configuration_errors_fail_fast_with_provider_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch, [_http_error(401, '{"error": "invalid api key"}')])
    adapter = OpenAICompatibleAdapter(_target(), "TEST_KEY")
    with pytest.raises(RuntimeError, match=r"HTTP 401.*invalid api key"):
        adapter.generate([ITEM], GenerationConfig())


def test_null_content_and_malformed_bodies_do_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, [_ok(content=None, usage=None), {"unexpected": True}])
    adapter = OpenAICompatibleAdapter(_target(), "TEST_KEY")
    first, second = adapter.generate([ITEM, ITEM], GenerationConfig())
    assert first.raw_text == "" and first.parsed_answer is None and first.error is None
    assert second.error == "malformed provider response (no choices)"


def test_missing_api_key_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_KEY", raising=False)
    with pytest.raises(RuntimeError, match="TEST_KEY"):
        OpenAICompatibleAdapter(_target(), "TEST_KEY").generate([ITEM], GenerationConfig())


def test_replay_parses_text_and_flags_missing_items() -> None:
    adapter = ReplayAdapter({"q1": "The answer is (B)", "pinned": {"answer": "a", "text": "?"}})
    parsed, missing = adapter.generate(
        [ITEM, ITEM.model_copy(update={"id": "absent"})], GenerationConfig()
    )
    assert parsed.parsed_answer == "b"
    assert "Choices:" in str(parsed.request["prompt"])  # the rendered prompt is recorded
    assert missing.error is not None and missing.parsed_answer is None
    pinned = adapter.generate([ITEM.model_copy(update={"id": "pinned"})], GenerationConfig())[0]
    assert pinned.parsed_answer == "a"


class _Tensor:
    def __init__(self, values: list[Any]) -> None:
        self.values = values
        self.shape = (
            (1, len(values[0])) if values and isinstance(values[0], list) else (len(values),)
        )

    def __getitem__(self, index: Any) -> Any:
        result = self.values[index]
        return _Tensor(result) if isinstance(result, list) else result

    def __len__(self) -> int:
        return len(self.values)

    def tolist(self) -> list[Any]:
        return self.values


class _Tokenizer:
    chat_template = "{{ messages }}"
    eos_token_id = 0

    def __init__(self) -> None:
        self.rendered: list[object] = []

    def apply_chat_template(self, messages: object, **kwargs: object) -> str:
        self.rendered.append(messages)
        return "<chat>" + json.dumps(messages)

    def __call__(self, prompt: str, return_tensors: str) -> dict[str, _Tensor]:
        return {"input_ids": _Tensor([[1, 2, 3]])}

    def decode(self, ids: object, skip_special_tokens: bool) -> str:
        return " B "


class _Model:
    def generate(self, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(sequences=_Tensor([[1, 2, 3, 7, 8]]), scores=())

    def compute_transition_scores(self, *args: object, **kwargs: object) -> _Tensor:
        return _Tensor([[-0.25, -0.5]])


def test_local_adapter_uses_chat_template_and_records_logprobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokenizer = _Tokenizer()
    transformers = ModuleType("transformers")
    transformers.AutoTokenizer = SimpleNamespace(from_pretrained=lambda *a, **k: tokenizer)  # type: ignore[attr-defined]
    transformers.AutoModelForCausalLM = SimpleNamespace(from_pretrained=lambda *a, **k: _Model())  # type: ignore[attr-defined]
    torch = ModuleType("torch")
    torch.manual_seed = lambda seed: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setitem(sys.modules, "torch", torch)
    target = ModelTarget(id="local/m", adapter="huggingface_local", system_prompt="sys")
    response = HuggingFaceLocalAdapter(target).generate([ITEM], GenerationConfig(seed=1))[0]
    assert str(response.request["prompt"]).startswith("<chat>")
    assert tokenizer.rendered[0][0] == {"role": "system", "content": "sys"}  # type: ignore[index]
    assert response.parsed_answer == "b"
    assert response.token_logprobs == (-0.25, -0.5)
    assert response.token_count == 5


class _Flaky:
    adapter_id = "flaky"

    def __init__(self) -> None:
        self.calls = 0

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities()

    def generate(self, items: Any, config: GenerationConfig) -> list[ModelResponse]:
        self.calls += 1
        error = "transient" if self.calls == 1 else None
        return [
            ModelResponse(
                item_id=item.id,
                request={},
                normalized_request={},
                raw_text="b",
                parsed_answer=None if error else "b",
                error=error,
            )
            for item in items
        ]


def test_cache_never_persists_errors_and_ignores_budget_changes(tmp_path: Path) -> None:
    inner = _Flaky()
    target = ModelTarget(id="m", adapter="replay")
    cached = CachedAdapter(inner, target, tmp_path)
    assert cached.generate([ITEM], GenerationConfig())[0].error == "transient"
    assert list(tmp_path.rglob("*.json")) == []  # the failure is retried on resume
    assert cached.generate([ITEM], GenerationConfig())[0].parsed_answer == "b"
    raised = CachedAdapter(inner, target.model_copy(update={"request_limit": 5}), tmp_path)
    assert raised.generate([ITEM], GenerationConfig())[0].parsed_answer == "b"
    assert inner.calls == 2 and raised.hits == 1


def test_cache_treats_corrupt_entries_as_misses(tmp_path: Path) -> None:
    inner = _Flaky()
    inner.calls = 1  # succeed immediately
    cached = CachedAdapter(inner, ModelTarget(id="m", adapter="replay"), tmp_path)
    cached.generate([ITEM], GenerationConfig())
    (entry,) = tmp_path.rglob("*.json")
    entry.write_text("{truncated", encoding="utf-8")
    assert cached.generate([ITEM], GenerationConfig())[0].parsed_answer == "b"
    assert cached.misses == 2
