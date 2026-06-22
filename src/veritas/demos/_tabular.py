"""Shared CSV/TSV -> contract mapping for the demo adapters.

Eval tables need ``id, sequence, label, prediction`` (with an optional ``structure``
column and per-item metadata columns); reference tables need ``id, sequence`` (with an
optional ``structure``). Reference items carry a ``seen_reason`` -- the adapter states
*why* the model is considered to have seen each reference sequence.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import polars as pl

from veritas.contracts import EvalItem, ReferenceItem, SeqType
from veritas.io._tables import read_table

_EVAL_REQUIRED = ("id", "sequence", "label", "prediction")
_REF_REQUIRED = ("id", "sequence")


def _require_columns(frame: pl.DataFrame, required: Sequence[str], path: Path) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")


def _structure_path(value: object, structures_dir: Path | None) -> Path | None:
    if structures_dir is None or value is None or value == "":
        return None
    return structures_dir / str(value)


def eval_items_from_table(
    path: Path,
    *,
    seq_type: SeqType,
    metadata_columns: Sequence[str] = (),
    structures_dir: Path | None = None,
    structure_column: str = "structure",
) -> tuple[EvalItem, ...]:
    frame = read_table(path)
    _require_columns(frame, _EVAL_REQUIRED, path)
    has_structure = structure_column in frame.columns
    items: list[EvalItem] = []
    for row in frame.iter_rows(named=True):
        metadata: dict[str, str | int | float | bool] = {
            column: str(row[column])
            for column in metadata_columns
            if column in frame.columns and row[column] is not None
        }
        structure = (
            _structure_path(row[structure_column], structures_dir) if has_structure else None
        )
        items.append(
            EvalItem(
                id=str(row["id"]),
                seq_type=seq_type,
                sequence=str(row["sequence"]),
                label=float(row["label"]),
                prediction=float(row["prediction"]),
                structure_path=structure,
                metadata=metadata,
            )
        )
    return tuple(items)


def reference_items_from_table(
    path: Path,
    *,
    seq_type: SeqType,
    seen_reason: str,
    structures_dir: Path | None = None,
    structure_column: str = "structure",
) -> tuple[ReferenceItem, ...]:
    frame = read_table(path)
    _require_columns(frame, _REF_REQUIRED, path)
    has_structure = structure_column in frame.columns
    items: list[ReferenceItem] = []
    for row in frame.iter_rows(named=True):
        structure = (
            _structure_path(row[structure_column], structures_dir) if has_structure else None
        )
        items.append(
            ReferenceItem(
                id=str(row["id"]),
                seq_type=seq_type,
                sequence=str(row["sequence"]),
                structure_path=structure,
                seen_reason=seen_reason,
            )
        )
    return tuple(items)
