from __future__ import annotations

import pytest

from veritas.benchmark_integrity.contracts import BenchmarkItem, Choice, TaskType
from veritas.benchmark_integrity.prompting import (
    TEMPLATE_KEY,
    chat_messages,
    format_prompt,
    normalize_answer,
    parse_answer,
)


def _item(ids: list[str], texts: list[str] | None = None) -> BenchmarkItem:
    values = texts or [f"text {index}" for index in range(len(ids))]
    return BenchmarkItem(
        id="x",
        prompt="Question?",
        expected_output=ids[0],
        task_type=TaskType.MULTIPLE_CHOICE,
        choices=tuple(Choice(id=i, text=t) for i, t in zip(ids, values, strict=True)),
    )


ABCD = _item(list("abcd"), ["54", "56", "64", "78"])
THIRTEEN = _item(list("abcdefghijklm"))


@pytest.mark.parametrize(
    ("item", "text", "expected"),
    [
        (ABCD, "b", "b"),
        (ABCD, "B.", "b"),
        (ABCD, "The answer is B", "b"),
        (ABCD, "Answer: (B)", "b"),
        (ABCD, "**C**", "c"),
        (ABCD, "The correct answer is **C**.", "c"),
        (ABCD, "A is tempting, but the answer is D", "d"),
        (ABCD, "Final answer: B", "b"),
        (ABCD, "Option C: 64", "c"),
        (ABCD, "(d) 78", "d"),
        (ABCD, "a", "a"),
        (ABCD, "The answer is 56", "b"),
        (ABCD, "56", "b"),
        (ABCD, "The answer is a tricky one", None),
        (ABCD, "56 is bigger than 54", None),
        (ABCD, "I don't know", None),
        (ABCD, "", None),
        (THIRTEEN, "I think the answer is C", "c"),
        (THIRTEEN, "I", "i"),
        (_item(["option_1", "option_2"]), "The answer is option_2", "option_2"),
        (_item(["option_1", "option_2"]), "option_2.", "option_2"),
        (_item(["1", "2", "3"]), "Answer: 3", "3"),
    ],
)
def test_parse_answer(item: BenchmarkItem, text: str, expected: str | None) -> None:
    assert parse_answer(item, text) == expected


def test_parse_answer_returns_text_for_open_ended_items() -> None:
    item = BenchmarkItem(id="o", prompt="p", expected_output="x", task_type=TaskType.OPEN_ENDED)
    assert parse_answer(item, "  42 \n") == "42"


@pytest.mark.parametrize(
    ("template", "marker"),
    [("default", "Choices:\na. 54"), ("qa_block", "Options:\n(a) 54"), ("inline", "a) 54 | b) 56")],
)
def test_format_prompt_templates(template: str, marker: str) -> None:
    item = ABCD.model_copy(update={"metadata": {TEMPLATE_KEY: template}})
    assert marker in format_prompt(item)
    assert format_prompt(item, "Be terse.").startswith("Be terse.\n\n")


def test_unknown_template_falls_back_to_default() -> None:
    item = ABCD.model_copy(update={"metadata": {TEMPLATE_KEY: "nope"}})
    assert format_prompt(item) == format_prompt(ABCD)


def test_open_ended_templates_wrap_the_question() -> None:
    base = BenchmarkItem(id="o", prompt="2+2?", expected_output="4", task_type=TaskType.OPEN_ENDED)
    assert format_prompt(base) == "2+2?"
    assert format_prompt(base.model_copy(update={"metadata": {TEMPLATE_KEY: "qa_block"}})) == (
        "Question:\n2+2?\n\nAnswer:"
    )
    assert format_prompt(base.model_copy(update={"metadata": {TEMPLATE_KEY: "inline"}})) == (
        "Q: 2+2?\nA:"
    )


def test_chat_messages_add_system_prompt_and_choices() -> None:
    assert chat_messages(ABCD, "sys")[0] == {"role": "system", "content": "sys"}
    chat = ABCD.model_copy(update={"prompt": ({"role": "user", "content": "Q?"},)})
    messages = chat_messages(chat, "sys")
    assert [m["role"] for m in messages] == ["system", "user", "user"]
    assert "Choices:" in str(messages[-1]["content"])
    with_system = chat.model_copy(
        update={"prompt": ({"role": "system", "content": "own"}, {"role": "user", "content": "Q"})}
    )
    assert [m["content"] for m in chat_messages(with_system, "sys")][:1] == ["own"]


def test_normalize_answer() -> None:
    assert normalize_answer("  Paris.\n") == "paris"
    assert normalize_answer("New   York") == "new york"
