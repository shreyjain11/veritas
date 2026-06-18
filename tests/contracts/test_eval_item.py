"""EvalItem: validation, alphabet enforcement, immutability, round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from veritas.contracts import EvalItem, SeqType


def test_valid_protein_eval_item() -> None:
    item = EvalItem(id="e1", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.9)
    assert item.id == "e1"
    assert item.sequence == "MKV"
    assert item.label == 1.0
    assert item.prediction == 0.9


def test_valid_nucleotide_eval_item() -> None:
    item = EvalItem(id="n1", sequence="ACGT", seq_type=SeqType.NUCLEOTIDE, label=0.0)
    assert item.sequence == "ACGT"
    assert item.prediction is None


def test_sequence_normalized_to_uppercase() -> None:
    item = EvalItem(id="e1", sequence="acgt", seq_type=SeqType.NUCLEOTIDE, label=0.0)
    assert item.sequence == "ACGT"


def test_rejects_empty_id() -> None:
    with pytest.raises(ValidationError):
        EvalItem(id="", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0)


def test_rejects_empty_sequence() -> None:
    with pytest.raises(ValidationError):
        EvalItem(id="e1", sequence="", seq_type=SeqType.PROTEIN, label=1.0)


def test_rejects_invalid_protein_character() -> None:
    with pytest.raises(ValidationError):
        EvalItem(id="e1", sequence="MK1", seq_type=SeqType.PROTEIN, label=1.0)


def test_rejects_protein_letter_under_nucleotide_alphabet() -> None:
    # 'E' is a valid amino acid but not an IUPAC nucleotide code.
    with pytest.raises(ValidationError):
        EvalItem(id="n1", sequence="ACGE", seq_type=SeqType.NUCLEOTIDE, label=0.0)


def test_is_frozen() -> None:
    item = EvalItem(id="e1", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0)
    with pytest.raises(ValidationError):
        item.label = 0.0


def test_prediction_defaults_to_none() -> None:
    item = EvalItem(id="e1", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0)
    assert item.prediction is None


def test_metadata_defaults_empty() -> None:
    item = EvalItem(id="e1", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0)
    assert item.metadata == {}


def test_structure_path_defaults_to_none() -> None:
    item = EvalItem(id="e1", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0)
    assert item.structure_path is None


def test_structure_path_accepts_known_formats(tmp_path: Path) -> None:
    for suffix in (".pdb", ".cif", ".mmcif", ".ent"):
        item = EvalItem(
            id="e1",
            sequence="MKV",
            seq_type=SeqType.PROTEIN,
            label=1.0,
            structure_path=tmp_path / f"x{suffix}",
        )
        assert item.structure_path is not None


def test_structure_path_rejects_non_structure_suffix(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        EvalItem(
            id="e1",
            sequence="MKV",
            seq_type=SeqType.PROTEIN,
            label=1.0,
            structure_path=tmp_path / "x.txt",
        )


def test_round_trip_json() -> None:
    item = EvalItem(id="e1", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=0.5)
    assert EvalItem.model_validate_json(item.model_dump_json()) == item


def test_rejects_invalid_seq_type() -> None:
    with pytest.raises(ValidationError):
        EvalItem(id="e1", sequence="MKV", seq_type="bogus", label=1.0)  # type: ignore[arg-type]


def test_high_precision_prediction_survives_round_trip_byte_identically() -> None:
    value = 0.1 + 0.2  # 0.30000000000000004 — not exactly representable
    item = EvalItem(id="e1", sequence="MKV", seq_type=SeqType.PROTEIN, label=1.0, prediction=value)
    serialized = item.model_dump_json()
    reloaded = EvalItem.model_validate_json(serialized)
    assert reloaded.prediction == value
    assert reloaded.model_dump_json() == serialized
