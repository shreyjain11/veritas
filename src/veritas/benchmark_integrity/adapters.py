"""Provider-neutral model and benchmark adapters used by the v2 service."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

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
    """Deterministic fixture adapter; responses are keyed by benchmark item id."""

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
            raw = self._responses.get(item.id, "")
            if isinstance(raw, dict):
                text = str(raw.get("text", raw.get("answer", "")))
                answer = raw.get("answer", text)
                logprobs = tuple(float(v) for v in raw.get("token_logprobs", [])) or None
            else:
                text, answer, logprobs = str(raw), raw, None
            request = {
                "item_id": item.id,
                "prompt": item.prompt,
                "generation": config.model_dump(mode="json"),
            }
            result.append(
                ModelResponse(
                    item_id=item.id,
                    request=request,
                    normalized_request=request,
                    raw_text=text,
                    parsed_answer=answer,
                    token_logprobs=logprobs,
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
            prompt = format_prompt(item, self._target.system_prompt)
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
                "generation": config.model_dump(mode="json"),
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


class OpenAICompatibleAdapter:
    """Minimal OpenAI-compatible HTTP adapter using only the standard library."""

    adapter_id = "openai_compatible"

    def __init__(
        self,
        target: ModelTarget,
        api_key_env: str = "MODEL_API_KEY",
        *,
        require_api_key: bool = True,
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

    def capabilities(self) -> ModelCapabilities:
        return self._target.capabilities

    def generate(
        self, items: Sequence[BenchmarkItem], config: GenerationConfig
    ) -> Sequence[ModelResponse]:
        key = os.environ.get(self._api_key_env)
        if not key and self._require_api_key:
            raise RuntimeError(f"missing API key environment variable {self._api_key_env}")
        endpoint = self._target.endpoint
        if endpoint is None:  # constructor guard, retained for strict typing
            raise ValueError("openai_compatible adapter requires model.endpoint")
        responses: list[ModelResponse] = []
        for item in items:
            payload = {
                "model": self._target.id,
                "messages": _messages(item),
                **config.model_dump(mode="json"),
            }
            if self._target.capabilities.token_probabilities:
                payload["logprobs"] = True
            started = time.monotonic()
            headers = {"Content-Type": "application/json", "User-Agent": "veritas/2"}
            if key:
                headers["Authorization"] = f"Bearer {key}"
            request = Request(
                self._endpoint + "/chat/completions",
                data=json.dumps(payload).encode(),
                headers=headers,
                method="POST",
            )
            # B310: URL schemes and credentials are constrained in __init__ above.
            with urlopen(request, timeout=60) as handle:  # nosec B310
                body = json.loads(handle.read().decode())
            choice = body["choices"][0]
            text = choice.get("message", {}).get("content", "")
            responses.append(
                ModelResponse(
                    item_id=item.id,
                    request={"item_id": item.id, "prompt": item.prompt},
                    normalized_request={"item_id": item.id, "prompt": item.prompt},
                    raw_text=text,
                    parsed_answer=parse_answer(item, text),
                    token_logprobs=_openai_logprobs(choice),
                    latency_ms=(time.monotonic() - started) * 1000,
                    token_count=body.get("usage", {}).get("total_tokens"),
                    finish_reason=choice.get("finish_reason"),
                    provenance={"adapter": self.adapter_id, "endpoint": self._target.endpoint},
                )
            )
        return responses


class JsonlBenchmarkAdapter:
    adapter_id = "jsonl"

    def load(self, config: Mapping[str, object]) -> Benchmark:
        path = Path(str(config["path"]))
        task_type = TaskType(str(config.get("task_type", "multiple_choice")))
        visibility = Visibility(str(config.get("visibility", "public")))
        items = tuple(
            BenchmarkItem.model_validate(json.loads(line))
            for line in path.read_text().splitlines()
            if line.strip()
        )
        return Benchmark(
            id=str(config.get("id", path.stem)),
            version=str(config.get("version", "1")),
            items=items,
            task_type=task_type,
            visibility=visibility,
            scoring=ScoringSpec.model_validate(config.get("scoring", {})),
        )


def _messages(item: BenchmarkItem) -> list[dict[str, object]]:
    if isinstance(item.prompt, tuple):
        return [dict(message) for message in item.prompt]
    return [{"role": "user", "content": format_prompt(item)}]


def format_prompt(item: BenchmarkItem, system_prompt: str | None = None) -> str:
    if isinstance(item.prompt, tuple):
        prompt = "\n".join(str(message.get("content", "")) for message in item.prompt)
    else:
        prompt = item.prompt
    if item.choices:
        choices = "\n".join(f"{choice.id}. {choice.text}" for choice in item.choices)
        prompt = f"{prompt}\n\nChoices:\n{choices}\n\nAnswer with the choice label only."
    return f"{system_prompt}\n\n{prompt}" if system_prompt else prompt


def parse_answer(item: BenchmarkItem, text: str) -> str:
    if not item.choices:
        return text.strip()
    labels = {choice.id.casefold(): choice.id for choice in item.choices}
    match = re.search(r"\b([A-Za-z0-9]+)\b", text.strip())
    if match and match.group(1).casefold() in labels:
        return labels[match.group(1).casefold()]
    return text.strip()


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
