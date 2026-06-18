"""Prediction-table loading: CSV/TSV/parquet converge to an identical PredictionSet."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from veritas.io import load_predictions


def _write_delimited(path: Path, sep: str) -> None:
    path.write_text(f"id{sep}prediction\ne1{sep}0.1\ne2{sep}0.2\n")


def test_load_csv(tmp_path: Path) -> None:
    path = tmp_path / "preds.csv"
    _write_delimited(path, ",")
    assert load_predictions(path).as_mapping() == {"e1": 0.1, "e2": 0.2}


def test_load_tsv(tmp_path: Path) -> None:
    path = tmp_path / "preds.tsv"
    _write_delimited(path, "\t")
    assert load_predictions(path).as_mapping() == {"e1": 0.1, "e2": 0.2}


def test_load_parquet(tmp_path: Path) -> None:
    path = tmp_path / "preds.parquet"
    pl.DataFrame({"id": ["e1", "e2"], "prediction": [0.1, 0.2]}).write_parquet(path)
    assert load_predictions(path).as_mapping() == {"e1": 0.1, "e2": 0.2}


def test_all_formats_yield_identical_prediction_set(tmp_path: Path) -> None:
    csv_path = tmp_path / "p.csv"
    tsv_path = tmp_path / "p.tsv"
    parquet_path = tmp_path / "p.parquet"
    _write_delimited(csv_path, ",")
    _write_delimited(tsv_path, "\t")
    pl.DataFrame({"id": ["e1", "e2"], "prediction": [0.1, 0.2]}).write_parquet(parquet_path)
    from_csv = load_predictions(csv_path)
    from_tsv = load_predictions(tsv_path)
    from_parquet = load_predictions(parquet_path)
    assert from_csv == from_tsv == from_parquet


def test_missing_required_column_errors(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("id,score\ne1,0.1\n")
    with pytest.raises(ValueError):
        load_predictions(path)


def test_unsupported_extension_errors(tmp_path: Path) -> None:
    path = tmp_path / "preds.json"
    path.write_text("{}")
    with pytest.raises(ValueError):
        load_predictions(path)
