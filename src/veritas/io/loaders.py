"""High-level loaders that assemble core contracts from files."""

from __future__ import annotations

from pathlib import Path

from veritas.contracts import (
    Benchmark,
    EvalItem,
    MetricSpec,
    ReferenceItem,
    SeqType,
    SplitSpec,
)
from veritas.io._tables import read_table
from veritas.io.fasta import read_fasta

_REQUIRED_COLUMNS = ("id", "label", "prediction")


def load_benchmark(
    sequences: Path,
    table: Path,
    *,
    seq_type: SeqType,
    metric: MetricSpec,
    split: SplitSpec,
) -> Benchmark:
    """Build a Benchmark from a FASTA of eval sequences and a label/prediction table.

    The table must have columns ``id``, ``label``, ``prediction``. Every sequence
    id must have a matching table row (otherwise a :class:`ValueError` is raised).
    """
    records = read_fasta(sequences, seq_type=seq_type)
    frame = read_table(table)
    missing = [column for column in _REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"benchmark table missing required columns: {missing}")

    labels: dict[str, float] = {}
    predictions: dict[str, float] = {}
    for row in frame.iter_rows(named=True):
        item_id = str(row["id"])
        labels[item_id] = float(row["label"])
        predictions[item_id] = float(row["prediction"])

    eval_items: list[EvalItem] = []
    for record in records:
        if record.id not in labels:
            raise ValueError(f"no table row for sequence id: {record.id}")
        eval_items.append(
            EvalItem(
                id=record.id,
                seq_type=seq_type,
                sequence=record.sequence,
                label=labels[record.id],
                prediction=predictions[record.id],
            )
        )

    return Benchmark(name=sequences.stem, eval_items=tuple(eval_items), split=split, metric=metric)


def load_reference_set(sequences: Path, *, seq_type: SeqType) -> tuple[ReferenceItem, ...]:
    records = read_fasta(sequences, seq_type=seq_type)
    return tuple(
        ReferenceItem(id=record.id, seq_type=seq_type, sequence=record.sequence)
        for record in records
    )
