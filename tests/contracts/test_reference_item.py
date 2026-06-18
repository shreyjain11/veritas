"""ReferenceItem: validation, optional structure path, immutability, round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from veritas.contracts import ReferenceItem, SeqType


def test_valid_reference_item() -> None:
    ref = ReferenceItem(id="r1", sequence="MKV", seq_type=SeqType.PROTEIN, seen_reason="train set")
    assert ref.id == "r1"
    assert ref.structure_path is None
    assert ref.seen_reason == "train set"


def test_structure_path_accepts_known_formats(tmp_path: Path) -> None:
    for suffix in (".pdb", ".cif", ".mmcif", ".ent"):
        ref = ReferenceItem(
            id="r1",
            sequence="MKV",
            seq_type=SeqType.PROTEIN,
            structure_path=tmp_path / f"x{suffix}",
        )
        assert ref.structure_path is not None


def test_rejects_non_structure_suffix(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        ReferenceItem(
            id="r1",
            sequence="MKV",
            seq_type=SeqType.PROTEIN,
            structure_path=tmp_path / "x.txt",
        )


def test_rejects_invalid_sequence_character() -> None:
    with pytest.raises(ValidationError):
        ReferenceItem(id="r1", sequence="MK1", seq_type=SeqType.PROTEIN)


def test_is_frozen() -> None:
    ref = ReferenceItem(id="r1", sequence="MKV", seq_type=SeqType.PROTEIN)
    with pytest.raises(ValidationError):
        ref.id = "r2"


def test_round_trip_json() -> None:
    ref = ReferenceItem(id="r1", sequence="MKV", seq_type=SeqType.PROTEIN, seen_reason="x")
    assert ReferenceItem.model_validate_json(ref.model_dump_json()) == ref
