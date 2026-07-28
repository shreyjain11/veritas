"""Reproducible, answer-preserving transforms for initial v2 modalities."""

from __future__ import annotations

import hashlib
import random
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from veritas.benchmark_integrity.contracts import BenchmarkItem, Transformation, ValidationStatus


@dataclass(frozen=True)
class DerivedItem:
    item: BenchmarkItem
    transformation: Transformation


class Transform(Protocol):
    transform_id: str

    def apply(self, item: BenchmarkItem, seed: int) -> DerivedItem: ...


class ChoicePermutation:
    transform_id = "choice_permutation"

    def apply(self, item: BenchmarkItem, seed: int) -> DerivedItem:
        if not item.choices:
            raise ValueError("choice_permutation requires a multiple-choice item")
        choices = list(item.choices)
        # This RNG is deliberately reproducible experimental sampling, not cryptography.
        random.Random(seed).shuffle(choices)  # nosec B311
        child_id = f"{item.id}::choice-order::{seed}"
        child = item.model_copy(update={"id": child_id, "choices": tuple(choices)})
        return _derived(
            item,
            child,
            self.transform_id,
            seed,
            ValidationStatus.VALID,
            "deterministic permutation",
        )


class FormattingTransform:
    transform_id = "formatting"

    def apply(self, item: BenchmarkItem, seed: int) -> DerivedItem:
        if not isinstance(item.prompt, str):
            raise ValueError("formatting requires a text prompt")
        prompt = re.sub(r"\s+", " ", item.prompt).strip().replace(". ", ".\n\n")
        child = item.model_copy(update={"id": f"{item.id}::format::{seed}", "prompt": prompt})
        return _derived(
            item,
            child,
            self.transform_id,
            seed,
            ValidationStatus.VALID,
            "deterministic whitespace normalization",
        )


class ChoiceLabelRemap:
    transform_id = "choice_label_remap"

    def apply(self, item: BenchmarkItem, seed: int) -> DerivedItem:
        if not item.choices:
            raise ValueError("choice_label_remap requires a multiple-choice item")
        labels = [f"option_{index + 1}" for index in range(len(item.choices))]
        mapping = {choice.id: label for choice, label in zip(item.choices, labels, strict=True)}
        choices = tuple(
            choice.model_copy(update={"id": mapping[choice.id]}) for choice in item.choices
        )
        expected = mapping[str(item.expected_output)]
        child = item.model_copy(
            update={
                "id": f"{item.id}::label-remap::{seed}",
                "choices": choices,
                "expected_output": expected,
            }
        )
        return _derived(
            item,
            child,
            self.transform_id,
            seed,
            ValidationStatus.VALID,
            "deterministic bijective label remapping",
        )


class IdentifierTransform:
    transform_id = "identifier"

    def apply(self, item: BenchmarkItem, seed: int) -> DerivedItem:
        if not isinstance(item.prompt, str):
            raise ValueError("identifier requires a text prompt")
        replacement = f"value_{seed % 997}"
        prompt = re.sub(r"\b(?:foo|bar|baz|x|y|z)\b", replacement, item.prompt)
        child = item.model_copy(update={"id": f"{item.id}::identifier::{seed}", "prompt": prompt})
        return _derived(
            item,
            child,
            self.transform_id,
            seed,
            ValidationStatus.UNCERTAIN,
            "rule-based identifier replacement",
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
    transform = TRANSFORMS.get(kind)
    if transform is None:
        raise ValueError(f"unknown transform {kind!r}; available: {sorted(TRANSFORMS)}")
    return tuple(
        transform.apply(item, seed + offset)
        for item in items
        for offset in range(variants_per_item)
    )


def _derived(
    parent: BenchmarkItem,
    child: BenchmarkItem,
    family: str,
    seed: int,
    status: ValidationStatus,
    method: str,
) -> DerivedItem:
    payload = child.model_dump_json().encode()
    transformation = Transformation(
        id=f"{family}:{child.id}",
        family=family,
        parent_item_id=parent.id,
        child_item_id=child.id,
        seed=seed,
        validation=status,
        validation_method=method,
        expected_output=parent.expected_output,
        content_hash=hashlib.sha256(payload).hexdigest(),
    )
    return DerivedItem(item=child, transformation=transformation)
