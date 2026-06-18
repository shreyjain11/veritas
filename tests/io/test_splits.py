"""Split-file loading: partition assignment and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from veritas.contracts import Partition
from veritas.io import load_splits


def test_load_split_assigns_partitions(tmp_path: Path) -> None:
    path = tmp_path / "split.csv"
    path.write_text("id,partition\ne1,eval\nt1,train\nr1,reference\n")
    assert load_splits(path) == {
        "e1": Partition.EVAL,
        "t1": Partition.TRAIN,
        "r1": Partition.REFERENCE,
    }


def test_rejects_unknown_partition(tmp_path: Path) -> None:
    path = tmp_path / "split.csv"
    path.write_text("id,partition\ne1,validation\n")
    with pytest.raises(ValueError):
        load_splits(path)


def test_missing_columns_errors(tmp_path: Path) -> None:
    path = tmp_path / "split.csv"
    path.write_text("id,group\ne1,eval\n")
    with pytest.raises(ValueError):
        load_splits(path)


def test_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "split.csv"
    path.write_text("id,partition\ne1,eval\ne1,train\n")
    with pytest.raises(ValueError):
        load_splits(path)
