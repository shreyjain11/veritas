from __future__ import annotations

import pytest

from veritas.benchmark_integrity.contracts import (
    BenchmarkItem,
    Choice,
    TaskType,
    ValidationStatus,
)
from veritas.benchmark_integrity.prompting import TEMPLATE_KEY, format_prompt
from veritas.benchmark_integrity.transforms import generate


def _mcq(item_id: str = "q", answer: str = "b", n: int = 4) -> BenchmarkItem:
    labels = "abcdefgh"[:n]
    return BenchmarkItem(
        id=item_id,
        prompt="Which option is correct? Pick carefully.",
        expected_output=answer,
        task_type=TaskType.MULTIPLE_CHOICE,
        choices=tuple(Choice(id=label, text=f"text-{label}") for label in labels),
    )


def _answer_text(item: BenchmarkItem) -> str:
    return next(c.text for c in item.choices or () if c.id == item.expected_output)


@pytest.mark.parametrize("seed", range(40))
@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_choice_permutation_always_moves_the_answer_and_preserves_content(
    seed: int, n: int
) -> None:
    parent = _mcq(answer="a", n=n)
    child = generate([parent], "choice_permutation", 1, seed)[0]
    labels = [c.id for c in child.item.choices or ()]
    assert labels == [c.id for c in parent.choices or ()]  # labels stay positional
    assert sorted(c.text for c in child.item.choices or ()) == sorted(
        c.text for c in parent.choices or ()
    )
    assert child.item.expected_output != parent.expected_output  # never a no-op
    assert _answer_text(child.item) == _answer_text(parent)  # the key follows the content
    assert child.transformation.expected_output == child.item.expected_output
    assert child.transformation.validation is ValidationStatus.VALID


def test_choice_permutation_is_deterministic_and_varies_across_items() -> None:
    items = [_mcq(item_id=f"q{index}") for index in range(12)]
    first = generate(items, "choice_permutation", 1, 7)
    assert first == generate(items, "choice_permutation", 1, 7)
    orders = {tuple(d.transformation.parameters["order"]) for d in first}
    assert len(orders) > 1  # per-item RNG: not one permutation stamped on every item


def test_choice_permutation_flags_duplicate_option_texts_as_uncertain() -> None:
    item = BenchmarkItem(
        id="dup",
        prompt="p",
        expected_output="a",
        task_type=TaskType.MULTIPLE_CHOICE,
        choices=(
            Choice(id="a", text="same"),
            Choice(id="b", text="Same"),
            Choice(id="c", text="x"),
        ),
    )
    derived = generate([item], "choice_permutation", 1, 1)[0]
    assert derived.transformation.validation is ValidationStatus.UNCERTAIN


@pytest.mark.parametrize("seed", range(20))
def test_label_remap_is_bijective_disjoint_and_keeps_lineage(seed: int) -> None:
    parent = _mcq(answer="c")
    child = generate([parent], "choice_label_remap", 1, seed)[0]
    labels = [c.id for c in child.item.choices or ()]
    assert len(set(labels)) == len(labels)
    assert {label.casefold() for label in labels}.isdisjoint({"a", "b", "c", "d"})
    assert not {"A", "I"} & set(labels)  # never reuse labels that read as English words
    assert child.item.expected_output == labels[2]
    assert child.transformation.expected_output == child.item.expected_output
    assert [c.text for c in child.item.choices or ()] == [c.text for c in parent.choices or ()]


def test_label_remap_uses_more_than_one_scheme_across_seeds() -> None:
    schemes = {
        generate([_mcq()], "choice_label_remap", 1, seed)[0].transformation.parameters["scheme"]
        for seed in range(20)
    }
    assert schemes == {"numeric", "letters"}


def test_formatting_changes_template_but_not_content() -> None:
    parent = _mcq()
    child = generate([parent], "formatting", 1, 3)[0]
    assert child.item.metadata[TEMPLATE_KEY] in {"qa_block", "inline"}
    assert format_prompt(child.item) != format_prompt(parent)
    assert " ".join(str(child.item.prompt).split()) == " ".join(str(parent.prompt).split())
    assert child.item.choices == parent.choices
    assert child.item.expected_output == parent.expected_output


def test_formatting_skips_chat_prompts() -> None:
    item = BenchmarkItem(
        id="chat",
        prompt=({"role": "user", "content": "hi"},),
        expected_output="hello",
        task_type=TaskType.OPEN_ENDED,
    )
    assert generate([item], "formatting", 2, 1) == ()


def test_identifier_renaming_is_consistent_and_bijective() -> None:
    item = BenchmarkItem(
        id="alg",
        prompt="If x + y = 5 and x = 2, what is y?",
        expected_output="y = 3",
        task_type=TaskType.OPEN_ENDED,
    )
    child = generate([item], "identifier", 1, 42)[0]
    mapping = child.transformation.parameters["mapping"]
    assert set(mapping) == {"x", "y"}
    assert mapping["x"] != mapping["y"]  # distinct variables stay distinct
    assert child.item.prompt == (
        f"If {mapping['x']} + {mapping['y']} = 5 and {mapping['x']} = 2, what is {mapping['y']}?"
    )
    assert child.item.expected_output == f"{mapping['y']} = 3"
    assert child.transformation.validation is ValidationStatus.UNCERTAIN


def test_identifier_skips_prompts_without_identifiers() -> None:
    assert generate([_mcq()], "identifier", 1, 1) == ()


def test_generate_drops_duplicate_presentations_and_inapplicable_items() -> None:
    open_ended = BenchmarkItem(
        id="o", prompt="Say hi.", expected_output="hi", task_type=TaskType.OPEN_ENDED
    )
    two_choice = _mcq(item_id="two", answer="a", n=2)
    # A 2-option item has exactly one answer-moving permutation, so 5 requested variants
    # collapse to 1; the open-ended item has none.
    derived = generate([open_ended, two_choice], "choice_permutation", 5, 0)
    assert len(derived) == 1
    assert derived[0].transformation.parent_item_id == "two"


def test_generate_rejects_unknown_transform() -> None:
    with pytest.raises(ValueError, match="unknown transform"):
        generate([_mcq()], "paraphrase", 1, 0)
