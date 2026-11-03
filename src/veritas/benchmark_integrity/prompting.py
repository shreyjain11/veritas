"""Prompt rendering and answer parsing shared by every v2 model adapter.

Keeping these in one place guarantees that a transformed item is *presented* the
same way by the replay, OpenAI-compatible, and local adapters, and that a model's
answer is *read* the same way, so a paired comparison never measures an adapter
or parser difference instead of a model difference.
"""

from __future__ import annotations

import re

from veritas.benchmark_integrity.contracts import BenchmarkItem

# Reserved item-metadata key a transform uses to select an alternative prompt template.
TEMPLATE_KEY = "veritas_prompt_template"
TEMPLATES = ("default", "qa_block", "inline")
# Bump when rendering changes so content-addressed caches never replay stale prompts.
PROMPT_FORMAT_VERSION = "2"

_LABEL = r"(?P<label>[A-Za-z0-9_]+)(?![A-Za-z0-9_])"
_ANSWER_STATEMENT = re.compile(
    r"\b(?:final\s+)?answer\b\s*(?:is|would\s+be|should\s+be|:|=|-|\u2013)?\s*"
    r"(?:\*\*|__)?\s*(?:(?:option|choice|label)\s+)?[(\[]?\s*" + _LABEL,
    re.IGNORECASE,
)
_LEADING_LABEL = re.compile(
    r"^[\s*_`\"'\u201c\u2018(\[]*(?:(?:option|choice)\s+)?" + _LABEL,
    re.IGNORECASE,
)
_EDGE_NOISE = " \t\r\n*_`\"'\u201c\u201d\u2018\u2019()[]{}<>.:;,!?"


def prompt_text(item: BenchmarkItem) -> str:
    """The item's task text, flattening chat-style prompts to their message contents."""
    if isinstance(item.prompt, tuple):
        return "\n".join(str(message.get("content", "")) for message in item.prompt)
    return item.prompt


def template_of(item: BenchmarkItem) -> str:
    value = item.metadata.get(TEMPLATE_KEY, "default")
    return value if isinstance(value, str) and value in TEMPLATES else "default"


def format_prompt(item: BenchmarkItem, system_prompt: str | None = None) -> str:
    """Render the exact text a model sees for ``item`` (choices and template included)."""
    body = _render(item)
    return f"{system_prompt}\n\n{body}" if system_prompt else body


def chat_messages(item: BenchmarkItem, system_prompt: str | None = None) -> list[dict[str, object]]:
    """OpenAI-style chat messages for ``item``; chat prompts are passed through verbatim."""
    messages: list[dict[str, object]] = []
    if isinstance(item.prompt, tuple):
        messages = [dict(message) for message in item.prompt]
        if item.choices:
            # Choices are part of the task: append them so the model can answer with a label.
            messages.append({"role": "user", "content": _choices_block(item)})
    else:
        messages = [{"role": "user", "content": _render(item)}]
    if system_prompt and not any(message.get("role") == "system" for message in messages):
        messages.insert(0, {"role": "system", "content": system_prompt})
    return messages


def _choices_block(item: BenchmarkItem) -> str:
    choices = "\n".join(f"{choice.id}. {choice.text}" for choice in item.choices or ())
    return f"Choices:\n{choices}\n\nAnswer with the choice label only."


def _render(item: BenchmarkItem) -> str:
    text = prompt_text(item)
    template = template_of(item)
    if not item.choices:
        if template == "qa_block":
            return f"Question:\n{text}\n\nAnswer:"
        if template == "inline":
            return f"Q: {text}\nA:"
        return text
    if template == "qa_block":
        options = "\n".join(f"({choice.id}) {choice.text}" for choice in item.choices)
        return (
            f"Question:\n{text}\n\nOptions:\n{options}\n\n"
            "Respond with only the label of the correct option."
        )
    if template == "inline":
        options = " | ".join(f"{choice.id}) {choice.text}" for choice in item.choices)
        return f"{text}\nOptions: {options}\nReply with one option label."
    return f"{text}\n\n{_choices_block(item)}"


def parse_answer(item: BenchmarkItem, text: str) -> str | None:
    """Extract the model's answer.

    Open-ended items return the stripped text. Multiple-choice items return a declared
    choice id, or ``None`` when the response does not identify exactly one choice — an
    unparseable answer is never silently coerced into a label.
    """
    stripped = text.strip()
    if not item.choices:
        return stripped
    labels = {choice.id.casefold(): choice.id for choice in item.choices}
    bare = stripped.strip(_EDGE_NOISE)
    if bare.casefold() in labels:
        return labels[bare.casefold()]
    # The *last* explicit answer statement wins ("A is tempting, but the answer is C").
    for match in reversed(list(_ANSWER_STATEMENT.finditer(stripped))):
        label = _label_at(match, stripped, labels)
        if label is not None:
            return label
    leading = _LEADING_LABEL.match(stripped)
    if leading is not None:
        label = _label_at(leading, stripped, labels)
        if label is not None:
            return label
    return _unique_choice_text(item, bare, stripped)


def _label_at(match: re.Match[str], text: str, labels: dict[str, str]) -> str | None:
    token = match.group("label")
    if token.casefold() not in labels:
        return None
    # "a" and "I" double as English words: "the answer is a tricky one" names no label.
    if token in {"a", "I"} and re.match(r"\s+[A-Za-z]", text[match.end("label") :]):
        return None
    return labels[token.casefold()]


def _unique_choice_text(item: BenchmarkItem, bare: str, text: str) -> str | None:
    """Map a response that restates exactly one choice's text back to that choice."""
    folded = text.casefold()
    exact = [c.id for c in item.choices or () if c.text.strip().casefold() == bare.casefold()]
    if len(exact) == 1:
        return exact[0]
    mentioned = [
        choice.id
        for choice in item.choices or ()
        if len(choice.text.strip()) >= 2
        and re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(choice.text.strip().casefold())}(?![A-Za-z0-9_])",
            folded,
        )
    ]
    return mentioned[0] if len(mentioned) == 1 else None


def normalize_answer(value: object) -> str:
    """Whitespace- and case-insensitive form used by the ``normalized_match`` scorer."""
    return re.sub(r"\s+", " ", str(value)).strip().strip(".").casefold()
