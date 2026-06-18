"""High-level loaders: assemble a Benchmark / reference set from files."""

from __future__ import annotations

from pathlib import Path

import pytest

from veritas.contracts import MetricName, MetricSpec, SeqType, SplitSpec
from veritas.io import load_benchmark, load_reference_set


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    fasta = tmp_path / "eval.fasta"
    fasta.write_text(">e1\nMKV\n>e2\nGGG\n")
    table = tmp_path / "table.csv"
    table.write_text("id,label,prediction\ne1,1,0.9\ne2,0,0.2\n")
    return fasta, table


def test_load_benchmark_builds_eval_items(tmp_path: Path) -> None:
    fasta, table = _write_inputs(tmp_path)
    bench = load_benchmark(
        sequences=fasta,
        table=table,
        seq_type=SeqType.PROTEIN,
        metric=MetricSpec(name=MetricName.AUROC),
        split=SplitSpec(name="r", kind="random"),
    )
    assert {item.id for item in bench.eval_items} == {"e1", "e2"}


def test_load_benchmark_joins_labels_and_predictions(tmp_path: Path) -> None:
    fasta, table = _write_inputs(tmp_path)
    bench = load_benchmark(
        sequences=fasta,
        table=table,
        seq_type=SeqType.PROTEIN,
        metric=MetricSpec(name=MetricName.AUROC),
        split=SplitSpec(name="r", kind="random"),
    )
    by_id = {item.id: item for item in bench.eval_items}
    assert by_id["e1"].label == 1.0
    assert by_id["e1"].prediction == 0.9


def test_load_benchmark_errors_on_id_mismatch(tmp_path: Path) -> None:
    fasta = tmp_path / "eval.fasta"
    fasta.write_text(">e1\nMKV\n>e9\nGGG\n")
    table = tmp_path / "table.csv"
    table.write_text("id,label,prediction\ne1,1,0.9\n")
    with pytest.raises(ValueError):
        load_benchmark(
            sequences=fasta,
            table=table,
            seq_type=SeqType.PROTEIN,
            metric=MetricSpec(name=MetricName.AUROC),
            split=SplitSpec(name="r", kind="random"),
        )


def test_load_benchmark_errors_on_missing_columns(tmp_path: Path) -> None:
    fasta = tmp_path / "eval.fasta"
    fasta.write_text(">e1\nMKV\n")
    table = tmp_path / "table.csv"
    table.write_text("id,label\ne1,1\n")  # no prediction column
    with pytest.raises(ValueError):
        load_benchmark(
            sequences=fasta,
            table=table,
            seq_type=SeqType.PROTEIN,
            metric=MetricSpec(name=MetricName.AUROC),
            split=SplitSpec(name="r", kind="random"),
        )


def test_load_reference_set(tmp_path: Path) -> None:
    fasta = tmp_path / "ref.fasta"
    fasta.write_text(">r1\nMKV\n>r2\nGGG\n")
    refs = load_reference_set(fasta, seq_type=SeqType.PROTEIN)
    assert {ref.id for ref in refs} == {"r1", "r2"}
