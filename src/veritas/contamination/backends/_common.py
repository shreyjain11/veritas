"""Shared helpers for sequence-search backends."""

from __future__ import annotations

from collections.abc import Sequence

from veritas.contracts import EvalItem, ReferenceItem


def to_fasta(items: Sequence[EvalItem] | Sequence[ReferenceItem]) -> str:
    return "".join(f">{item.id}\n{item.sequence}\n" for item in items)
