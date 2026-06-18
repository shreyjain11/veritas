"""Load a declared split file into an id -> Partition assignment."""

from __future__ import annotations

from pathlib import Path

from veritas.contracts import Partition
from veritas.io._tables import read_table

_REQUIRED_COLUMNS = ("id", "partition")


def load_splits(path: Path) -> dict[str, Partition]:
    frame = read_table(path)
    missing = [column for column in _REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"split file missing required columns: {missing}")
    assignment: dict[str, Partition] = {}
    for row in frame.iter_rows(named=True):
        item_id = str(row["id"])
        if item_id in assignment:
            raise ValueError(f"duplicate id in split file: {item_id}")
        raw = str(row["partition"])
        try:
            assignment[item_id] = Partition(raw)
        except ValueError as exc:
            raise ValueError(f"unknown partition {raw!r} for id {item_id}") from exc
    return assignment
