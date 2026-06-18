"""AuditInputs validates the audit world before any detector runs (Phase 6 decision 2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veritas.contracts import (
    AuditInputs,
    Benchmark,
    EvalItem,
    MetricName,
    MetricSpec,
    ReferenceItem,
    SeqType,
    SplitSpec,
)


def _benchmark(seq_type: SeqType = SeqType.PROTEIN) -> Benchmark:
    sequence = "MKV" if seq_type is SeqType.PROTEIN else "ACGT"
    return Benchmark(
        name="b",
        eval_items=(
            EvalItem(id="e", seq_type=seq_type, sequence=sequence, label=1.0, prediction=0.9),
        ),
        split=SplitSpec(name="s", kind="holdout"),
        metric=MetricSpec(name=MetricName.ACCURACY),
    )


def _ref(item_id: str, seq_type: SeqType = SeqType.PROTEIN) -> ReferenceItem:
    sequence = "MKV" if seq_type is SeqType.PROTEIN else "ACGT"
    return ReferenceItem(id=item_id, seq_type=seq_type, sequence=sequence)


def test_consistent_inputs_construct() -> None:
    inputs = AuditInputs(benchmark=_benchmark(), reference_items=(_ref("r"),))
    assert inputs.reference_items[0].id == "r"


def test_mixed_alphabet_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AuditInputs(
            benchmark=_benchmark(SeqType.PROTEIN),
            reference_items=(_ref("r", SeqType.NUCLEOTIDE),),
        )


def test_duplicate_reference_ids_are_rejected() -> None:
    with pytest.raises(ValidationError):
        AuditInputs(benchmark=_benchmark(), reference_items=(_ref("r"), _ref("r")))


def test_empty_reference_set_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AuditInputs(benchmark=_benchmark(), reference_items=())
