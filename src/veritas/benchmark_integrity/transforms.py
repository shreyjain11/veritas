"""Reproducible, answer-preserving transforms for initial v2 modalities.

Every transform is a pure function of ``(parent item, seed)``. A transform that does
not apply to an item (choice permutation on an open-ended item, identifier renaming on
a prompt without identifiers) returns ``None`` and is skipped, and :func:`generate`
drops exact duplicates, so a no-op variant can never inflate a robustness score.
"""

from __future__ import annotations

import hashlib
import random
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from veritas.benchmark_integrity.contracts import (
    BenchmarkItem,
    Choice,
    JsonValue,
    Transformation,
    ValidationStatus,
)
from veritas.benchmark_integrity.prompting import TEMPLATE_KEY, TEMPLATES, format_prompt


@dataclass(frozen=True)
class DerivedItem:
    item: BenchmarkItem
    transformation: Transformation


class Transform(Protocol):
    transform_id: str

    def apply(self, item: BenchmarkItem, seed: int) -> DerivedItem | None: ...


def _rng(family: str, item_id: str, seed: int) -> random.Random:
    """Per-item RNG, so items sharing a seed do not all receive the same permutation."""
    digest = hashlib.sha256(f"{family}\x00{seed}\x00{item_id}".encode()).digest()
    # Deliberately reproducible experimental sampling, not cryptography.
    return random.Random(int.from_bytes(digest[:8], "big"))  # nosec B311


class ChoicePermutation:
    """Shuffle option texts under fixed positional labels so the correct label moves.

    Labels stay in their canonical positional order (``a, b, c, d``) while the texts
    are permuted, which is the standard answer-position test: a model that tracks
    content still answers correctly; one that favors a position or memorized label
    does not. The correct answer is always moved to a different position.
    """

    transform_id = "choice_permutation"

    def apply(self, item: BenchmarkItem, seed: int) -> DerivedItem | None:
        if not item.choices or len(item.choices) < 2:
            return None
        labels = [choice.id for choice in item.choices]
        correct = labels.index(str(item.expected_output))
        order = list(range(len(labels)))
        _rng(self.transform_id, item.id, seed).shuffle(order)
        if order.index(correct) == correct:
            order = order[1:] + order[:1]  # rotating moves every element, incl. the answer
        choices = tuple(
            Choice(id=labels[position], text=item.choices[source].text)
            for position, source in enumerate(order)
        )
        expected = labels[order.index(correct)]
        child = item.model_copy(
            update={
                "id": f"{item.id}::choice-order::{seed}",
                "choices": choices,
                "expected_output": expected,
            }
        )
        unique_texts = len({choice.text.strip().casefold() for choice in item.choices}) == len(
            item.choices
        )
        return _derived(
            item,
            child,
            self.transform_id,
            seed,
            ValidationStatus.VALID if unique_texts else ValidationStatus.UNCERTAIN,
            "deterministic option-text permutation under positional labels"
            if unique_texts
            else "permutation of an item with duplicate option texts",
            {
                "order": list(order),
                "answer_moved_from": labels[correct],
                "answer_moved_to": expected,
            },
        )


class ChoiceLabelRemap:
    """Replace option labels with a fresh bijective scheme (numerals or unused letters)."""

    transform_id = "choice_label_remap"
    _LETTERS = tuple(chr(code) for code in range(ord("A"), ord("Z") + 1) if chr(code) not in "AI")

    def apply(self, item: BenchmarkItem, seed: int) -> DerivedItem | None:
        if not item.choices:
            return None
        rng = _rng(self.transform_id, item.id, seed)
        originals = {choice.id.casefold() for choice in item.choices}
        count = len(item.choices)
        schemes = ["numeric", "letters"]
        rng.shuffle(schemes)
        labels: list[str] | None = None
        scheme = ""
        for scheme in schemes:
            labels = self._labels(scheme, count, originals, rng)
            if labels is not None:
                break
        if labels is None:  # pragma: no cover - needs >24 options that also use numerals
            scheme, labels = "prefixed", [f"L{index + 1}" for index in range(count)]
        mapping = {choice.id: label for choice, label in zip(item.choices, labels, strict=True)}
        choices = tuple(
            choice.model_copy(update={"id": mapping[choice.id]}) for choice in item.choices
        )
        child = item.model_copy(
            update={
                "id": f"{item.id}::label-remap::{seed}",
                "choices": choices,
                "expected_output": mapping[str(item.expected_output)],
            }
        )
        return _derived(
            item,
            child,
            self.transform_id,
            seed,
            ValidationStatus.VALID,
            "deterministic bijective label remapping",
            {"scheme": scheme, "mapping": dict(mapping)},
        )

    def _labels(
        self, scheme: str, count: int, originals: set[str], rng: random.Random
    ) -> list[str] | None:
        if scheme == "numeric":
            labels = [str(index + 1) for index in range(count)]
        else:
            pool = [letter for letter in self._LETTERS if letter.casefold() not in originals]
            if len(pool) < count:
                return None
            start = rng.randrange(0, len(pool) - count + 1)
            labels = pool[start : start + count]
        return None if {label.casefold() for label in labels} & originals else labels


class FormattingTransform:
    """Change the prompt template and whitespace layout; content and labels are kept."""

    transform_id = "formatting"
    _LAYOUTS = ("paragraphs", "single_line")

    def apply(self, item: BenchmarkItem, seed: int) -> DerivedItem | None:
        if not isinstance(item.prompt, str):
            return None
        rng = _rng(self.transform_id, item.id, seed)
        template = rng.choice([name for name in TEMPLATES if name != "default"])
        layout = rng.choice(self._LAYOUTS)
        collapsed = re.sub(r"\s+", " ", item.prompt).strip()
        prompt = collapsed if layout == "single_line" else re.sub(r"([.?!]) ", r"\1\n\n", collapsed)
        child = item.model_copy(
            update={
                "id": f"{item.id}::format::{seed}",
                "prompt": prompt,
                "metadata": {**item.metadata, TEMPLATE_KEY: template},
            }
        )
        return _derived(
            item,
            child,
            self.transform_id,
            seed,
            ValidationStatus.VALID,
            "prompt-template and whitespace change; task text and options preserved",
            {"template": template, "layout": layout},
        )


class IdentifierTransform:
    """Consistently rename placeholder identifiers (each name maps to a distinct name).

    Marked ``uncertain``: a rule cannot prove that ``x`` is a variable rather than, e.g.,
    a multiplication sign, so these variants are excluded from the robust score.
    """

    transform_id = "identifier"
    _PATTERN = re.compile(r"\b(?:foo|bar|baz|qux|x|y|z)\b")
    _NAMES = ("alpha", "beta", "gamma", "delta", "kappa", "sigma", "omega", "theta", "lambda")

    def apply(self, item: BenchmarkItem, seed: int) -> DerivedItem | None:
        if not isinstance(item.prompt, str):
            return None
        texts = [item.prompt, *(choice.text for choice in item.choices or ())]
        found = list(
            dict.fromkeys(m.group(0) for text in texts for m in self._PATTERN.finditer(text))
        )
        if not found:
            return None
        rng = _rng(self.transform_id, item.id, seed)
        existing = {word.casefold() for text in texts for word in re.findall(r"\w+", text)}
        names = [name for name in self._NAMES if name not in existing]
        rng.shuffle(names)
        if len(names) < len(found):
            names += [f"{names[0] if names else 'v'}_{index}" for index in range(len(found))]
        mapping = dict(zip(found, names, strict=False))

        def rename(text: str) -> str:
            return self._PATTERN.sub(lambda match: mapping[match.group(0)], text)

        update: dict[str, object] = {
            "id": f"{item.id}::identifier::{seed}",
            "prompt": rename(item.prompt),
        }
        if item.choices:
            update["choices"] = tuple(
                choice.model_copy(update={"text": rename(choice.text)}) for choice in item.choices
            )
        elif isinstance(item.expected_output, str):
            update["expected_output"] = rename(item.expected_output)
        child = item.model_copy(update=update)
        return _derived(
            item,
            child,
            self.transform_id,
            seed,
            ValidationStatus.UNCERTAIN,
            "rule-based consistent identifier renaming",
            {"mapping": dict(mapping)},
        )


TRANSFORMS: dict[str, Transform] = {
    "choice_permutation": ChoicePermutation(),
    "choice_label_remap": ChoiceLabelRemap(),
    "formatting": FormattingTransform(),
    "identifier": IdentifierTransform(),
}


def generate(
    items: Sequence[BenchmarkItem], kind: str, variants_per_item: int, seed: int
) -> tuple[DerivedItem, ...]:
    """Up to ``variants_per_item`` distinct variants per item; inapplicable items are skipped."""
    transform = TRANSFORMS.get(kind)
    if transform is None:
        raise ValueError(f"unknown transform {kind!r}; available: {sorted(TRANSFORMS)}")
    derived: list[DerivedItem] = []
    for item in items:
        seen: set[str] = set()
        for offset in range(variants_per_item):
            value = transform.apply(item, seed + offset)
            if value is None:
                continue
            rendered = format_prompt(value.item)
            if rendered in seen:
                continue  # an identical presentation is a replicate, not a new variant
            seen.add(rendered)
            derived.append(value)
    return tuple(derived)


def _derived(
    parent: BenchmarkItem,
    child: BenchmarkItem,
    family: str,
    seed: int,
    status: ValidationStatus,
    method: str,
    parameters: dict[str, JsonValue],
) -> DerivedItem:
    payload = child.model_dump_json().encode()
    transformation = Transformation(
        id=f"{family}:{child.id}",
        family=family,
        parent_item_id=parent.id,
        child_item_id=child.id,
        parameters=parameters,
        seed=seed,
        validation=status,
        validation_method=method,
        expected_output=child.expected_output,
        content_hash=hashlib.sha256(payload).hexdigest(),
    )
    return DerivedItem(item=child, transformation=transformation)
