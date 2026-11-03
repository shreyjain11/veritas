"""Provider-neutral model and benchmark adapters used by the v2 service."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from pydantic import ValidationError

from veritas.benchmark_integrity.contracts import (
    Benchmark,
    BenchmarkItem,
    GenerationConfig,
    ModelCapabilities,
    ModelResponse,
    ModelTarget,
    ScoringSpec,
    TaskType,
    Visibility,
)
from veritas.benchmark_integrity.prompting import (
    chat_messages,
    format_prompt,
    parse_answer,
)

__all__ = [
    "BenchmarkAdapter",
    "HuggingFaceLocalAdapter",
    "JsonlBenchmarkAdapter",
    "ModelAdapter",
    "OpenAICompatibleAdapter",
    "ReplayAdapter",
    "format_prompt",
    "parse_answer",
]

# generation.extra keys that configure Veritas itself and are never sent to a provider.
RESERVED_EXTRA_KEYS = frozenset(
    {"api_key_env", "responses", "max_retries", "timeout_s", "retry_backoff_s"}
)
_RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


def generation_record(config: GenerationConfig) -> dict[str, Any]:
    """Generation settings as recorded per response: Veritas-internal extras are dropped.

    In particular a replay table is never copied into every response it produced.
    """
    record = config.model_dump(mode="json")
    record["extra"] = {
        key: value for key, value in config.extra.items() if key not in RESERVED_EXTRA_KEYS
    }
    return record


class ModelAdapter(Protocol):
    adapter_id: str

    def capabilities(self) -> ModelCapabilities: ...

    def generate(
        self, items: Sequence[BenchmarkItem], config: GenerationConfig
    ) -> Sequence[ModelResponse]: ...


class BenchmarkAdapter(Protocol):
    adapter_id: str

    def load(self, config: Mapping[str, object]) -> Benchmark: ...


class ReplayAdapter:
    """Deterministic fixture adapter; responses are keyed by benchmark item id.

    A string response is treated as raw model text and parsed exactly like a live
    model's output; a ``{"answer": ...}`` object pins the parsed answer explicitly.
    An item with no recorded response is reported as an error, not as a wrong answer.
    """

    adapter_id = "replay"

    def __init__(self, responses: Mapping[str, object]) -> None:
        self._responses = responses

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(token_probabilities=True, deterministic_seed=True)

    def generate(
        self, items: Sequence[BenchmarkItem], config: GenerationConfig
    ) -> Sequence[ModelResponse]:
        result: list[ModelResponse] = []
        for item in items:
            request = {
                "item_id": item.id,
                "prompt": format_prompt(item),
                "generation": generation_record(config),
            }
            error: str | None = None
            logprobs: tuple[float, ...] | None = None
            if item.id not in self._responses:
                text, answer, error = "", None, "no replay response recorded for this item"
            else:
                raw = self._responses[item.id]
                if isinstance(raw, dict):
                    text = str(raw.get("text", raw.get("answer", "")))
                    answer = raw["answer"] if "answer" in raw else parse_answer(item, text)
                    logprobs = tuple(float(v) for v in raw.get("token_logprobs", [])) or None
                else:
                    text = str(raw)
                    answer = parse_answer(item, text)
            result.append(
                ModelResponse(
                    item_id=item.id,
                    request=request,
                    normalized_request=request,
                    raw_text=text,
                    parsed_answer=answer,
                    token_logprobs=logprobs,
                    error=error,
                    provenance={"adapter": self.adapter_id},
                )
            )
        return result


class HuggingFaceLocalAdapter:
    """Direct local Transformers adapter with generated-token log probabilities.

    Transformers and torch are optional dependencies and are imported only when
    this adapter is constructed, keeping the core package dependency-light.
    """

    adapter_id = "huggingface_local"

    def __init__(self, target: ModelTarget) -> None:
        try:
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
            )
        except ImportError as exc:
            raise RuntimeError(
                "huggingface_local requires `pip install veritas-leakage[local-model]`"
            ) from exc
        revision = target.revision or "main"
        self._target = target
        self._tokenizer: Any = AutoTokenizer.from_pretrained(
            target.id, revision=revision, trust_remote_code=False
        )
        self._model: Any = AutoModelForCausalLM.from_pretrained(
            target.id, revision=revision, trust_remote_code=False
        )

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(token_probabilities=True, deterministic_seed=True)

    def _prompt(self, item: BenchmarkItem) -> str:
        # Instruction-tuned checkpoints expect their own chat template; base models do not
        # ship one and receive the plain rendered prompt.
        if getattr(self._tokenizer, "chat_template", None):
            rendered: object = self._tokenizer.apply_chat_template(
                chat_messages(item, self._target.system_prompt),
                tokenize=False,
                add_generation_prompt=True,
            )
            return str(rendered)
        return format_prompt(item, self._target.system_prompt)

    def generate(
        self, items: Sequence[BenchmarkItem], config: GenerationConfig
    ) -> Sequence[ModelResponse]:
        try:
            import torch
        except ImportError as exc:  # pragma: no cover - constructor dependency includes torch
            raise RuntimeError("huggingface_local requires torch") from exc
        if config.seed is not None:
            torch.manual_seed(config.seed)
        responses: list[ModelResponse] = []
        for item in items:
            prompt = self._prompt(item)
            encoded = self._tokenizer(prompt, return_tensors="pt")
            started = time.monotonic()
            output = self._model.generate(
                **encoded,
                max_new_tokens=config.max_tokens,
                do_sample=config.temperature > 0,
                temperature=config.temperature if config.temperature > 0 else None,
                return_dict_in_generate=True,
                output_scores=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )
            input_length = int(encoded["input_ids"].shape[1])
            generated_ids = output.sequences[0][input_length:]
            text = self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
            transition = self._model.compute_transition_scores(
                output.sequences, output.scores, normalize_logits=True
            )
            logprobs = tuple(float(value) for value in transition[0].tolist())
            request = {
                "item_id": item.id,
                "prompt": prompt,
                "generation": generation_record(config),
            }
            responses.append(
                ModelResponse(
                    item_id=item.id,
                    request=request,
                    normalized_request=request,
                    raw_text=text,
                    parsed_answer=parse_answer(item, text),
                    token_logprobs=logprobs,
                    latency_ms=(time.monotonic() - started) * 1000,
                    token_count=input_length + len(generated_ids),
                    finish_reason="stop",
                    provenance={
                        "adapter": self.adapter_id,
                        "model_revision": self._target.revision or "main",
                    },
                )
            )
        return responses


class _TransientError(Exception):
    """A request that kept failing for reasons outside the audit configuration."""


class OpenAICompatibleAdapter:
    """Minimal OpenAI-compatible HTTP adapter using only the standard library.

    Transient failures (timeouts, connection errors, 408/409/425/429/5xx) are retried
    with exponential backoff and, if they persist, recorded as an errored response so
    one flaky request cannot discard a long run. Configuration errors (bad key, unknown
    model, malformed request) fail fast because every later request would fail too.
    """

    adapter_id = "openai_compatible"

    def __init__(
        self,
        target: ModelTarget,
        api_key_env: str = "MODEL_API_KEY",
        *,
        require_api_key: bool = True,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not target.endpoint:
            raise ValueError("openai_compatible adapter requires model.endpoint")
        parsed = urlsplit(target.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("model.endpoint must be an absolute HTTP(S) URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("model.endpoint must not contain embedded credentials")
        if parsed.query or parsed.fragment:
            raise ValueError("model.endpoint must not contain a query string or fragment")
        self._target = target
        self._endpoint = target.endpoint.rstrip("/")
        self._api_key_env = api_key_env
        self._require_api_key = require_api_key
        self._sleep = sleep
        extra = target.generation.extra
        self._max_retries = max(0, int(extra.get("max_retries", 3)))
        self._timeout = float(extra.get("timeout_s", 60))
        self._backoff = float(extra.get("retry_backoff_s", 1.0))

    def capabilities(self) -> ModelCapabilities:
        return self._target.capabilities

    def payload(self, item: BenchmarkItem, config: GenerationConfig) -> dict[str, Any]:
        """The exact JSON body sent for ``item`` (never contains credentials)."""
        payload: dict[str, Any] = {
            "model": self._target.id,
            "messages": chat_messages(item, self._target.system_prompt),
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        if config.seed is not None:
            payload["seed"] = config.seed
        if self._target.capabilities.token_probabilities:
            payload["logprobs"] = True
        payload.update(
            {key: value for key, value in config.extra.items() if key not in RESERVED_EXTRA_KEYS}
        )
        return payload

    def generate(
        self, items: Sequence[BenchmarkItem], config: GenerationConfig
    ) -> Sequence[ModelResponse]:
        key = os.environ.get(self._api_key_env)
        if not key and self._require_api_key:
            raise RuntimeError(f"missing API key environment variable {self._api_key_env}")
        responses: list[ModelResponse] = []
        for item in items:
            payload = self.payload(item, config)
            started = time.monotonic()
            provenance: dict[str, Any] = {
                "adapter": self.adapter_id,
                "endpoint": self._target.endpoint,
            }
            try:
                body, attempt = self._post(payload, key)
                choice = body["choices"][0]
                message = choice.get("message") or {}
                text = str(message.get("content") or "")
            except _TransientError as exc:
                responses.append(
                    _error_response(item, payload, str(exc), self._max_retries + 1, provenance)
                )
                continue
            except (KeyError, IndexError, TypeError, AttributeError):
                responses.append(
                    _error_response(
                        item, payload, "malformed provider response (no choices)", 1, provenance
                    )
                )
                continue
            raw_usage = body.get("usage")
            usage: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
            responses.append(
                ModelResponse(
                    item_id=item.id,
                    request=payload,
                    normalized_request=payload,
                    raw_text=text,
                    parsed_answer=parse_answer(item, text),
                    token_logprobs=_openai_logprobs(choice),
                    latency_ms=(time.monotonic() - started) * 1000,
                    token_count=usage.get("total_tokens"),
                    finish_reason=choice.get("finish_reason"),
                    attempt=attempt,
                    provenance=provenance,
                )
            )
        return responses

    def _post(self, payload: dict[str, Any], key: str | None) -> tuple[dict[str, Any], int]:
        headers = {"Content-Type": "application/json", "User-Agent": "veritas/2"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        data = json.dumps(payload).encode()
        last_error = "request failed"
        for attempt in range(1, self._max_retries + 2):
            request = Request(
                self._endpoint + "/chat/completions", data=data, headers=headers, method="POST"
            )
            try:
                # B310: URL schemes and credentials are constrained in __init__ above.
                with urlopen(request, timeout=self._timeout) as handle:  # nosec B310
                    body = json.loads(handle.read().decode())
                if not isinstance(body, dict):
                    raise _TransientError("provider returned non-object JSON")
                return body, attempt
            except HTTPError as exc:
                if exc.code not in _RETRYABLE_STATUS:
                    raise RuntimeError(
                        f"model endpoint rejected the request (HTTP {exc.code}): {_error_body(exc)}"
                    ) from exc
                last_error = f"HTTP {exc.code} after {attempt} attempt(s)"
            except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                last_error = f"{type(exc).__name__} after {attempt} attempt(s)"
            if attempt <= self._max_retries:
                self._sleep(self._backoff * 2 ** (attempt - 1))
        raise _TransientError(last_error)


def _error_body(exc: HTTPError) -> str:
    try:
        text = exc.read().decode("utf-8", "replace")
    except Exception:  # pragma: no cover - defensive: body may be unreadable
        return exc.reason if isinstance(exc.reason, str) else "no detail"
    return " ".join(text.split())[:300] or "no detail"


def _error_response(
    item: BenchmarkItem,
    payload: dict[str, Any],
    error: str,
    attempt: int,
    provenance: dict[str, Any],
) -> ModelResponse:
    return ModelResponse(
        item_id=item.id,
        request=payload,
        normalized_request=payload,
        raw_text="",
        parsed_answer=None,
        finish_reason="error",
        attempt=attempt,
        error=error,
        provenance=provenance,
    )


class JsonlBenchmarkAdapter:
    """Load one JSON benchmark item per line; ``task_type`` defaults to the benchmark's."""

    adapter_id = "jsonl"

    def load(self, config: Mapping[str, object]) -> Benchmark:
        if "path" not in config:
            raise ValueError("jsonl benchmark requires benchmark.path")
        path = Path(str(config["path"]))
        if not path.is_file():
            raise ValueError(f"benchmark file not found: {path}")
        task_type = TaskType(str(config.get("task_type", "multiple_choice")))
        visibility = Visibility(str(config.get("visibility", "public")))
        items: list[BenchmarkItem] = []
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: invalid JSON ({exc.msg})") from exc
            if isinstance(raw, dict):
                raw.setdefault("task_type", task_type.value)
            try:
                items.append(BenchmarkItem.model_validate(raw))
            except ValidationError as exc:
                first = exc.errors()[0]
                where = ".".join(str(part) for part in first["loc"]) or "item"
                raise ValueError(f"{path}:{number}: {where}: {first['msg']}") from exc
        if not items:
            raise ValueError(f"benchmark file {path} contains no items")
        try:
            return Benchmark(
                id=str(config.get("id", path.stem)),
                version=str(config.get("version", "1")),
                items=tuple(items),
                task_type=task_type,
                visibility=visibility,
                scoring=ScoringSpec.model_validate(config.get("scoring", {})),
            )
        except ValidationError as exc:
            raise ValueError(f"{path}: {exc.errors()[0]['msg']}") from exc


def _openai_logprobs(choice: Mapping[str, object]) -> tuple[float, ...] | None:
    payload = choice.get("logprobs")
    if not isinstance(payload, dict):
        return None
    content = payload.get("content")
    if not isinstance(content, list):
        return None
    values = [
        float(token["logprob"])
        for token in content
        if isinstance(token, dict) and isinstance(token.get("logprob"), int | float)
    ]
    return tuple(values) or None
