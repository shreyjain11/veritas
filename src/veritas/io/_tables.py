"""Tabular input reader: CSV/TSV/parquet -> polars (docs/PLAN.md decision #2)."""

from __future__ import annotations

from pathlib import Path

import polars as pl


def read_table(path: Path) -> pl.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pl.read_csv(path)
    if suffix == ".tsv":
        return pl.read_csv(path, separator="\t")
    if suffix == ".parquet":
        return pl.read_parquet(path)
    raise ValueError(f"unsupported table format: {suffix!r} (expected .csv, .tsv, or .parquet)")
