"""Load a model's per-example predictions into a PredictionSet."""

from __future__ import annotations

from pathlib import Path

from veritas.contracts import PredictionRecord, PredictionSet
from veritas.io._tables import read_table

_REQUIRED_COLUMNS = ("id", "prediction")


def load_predictions(path: Path) -> PredictionSet:
    frame = read_table(path)
    missing = [column for column in _REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"prediction table missing required columns: {missing}")
    # Sort by id for a deterministic record order across input formats.
    rows = frame.select(["id", "prediction"]).sort("id").iter_rows(named=True)
    records = tuple(
        PredictionRecord(item_id=str(row["id"]), value=float(row["prediction"])) for row in rows
    )
    return PredictionSet(records=records)
