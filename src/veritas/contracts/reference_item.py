"""ReferenceItem: a sequence (optionally a structure) the model effectively "saw"."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, ValidationInfo, field_validator

from veritas.contracts.base import FrozenModel
from veritas.contracts.enums import SeqType
from veritas.contracts.sequences import normalize_sequence_field
from veritas.contracts.structure import validate_structure_path


class ReferenceItem(FrozenModel):
    id: str = Field(min_length=1)
    seq_type: SeqType
    sequence: str = Field(min_length=1)
    structure_path: Path | None = None
    seen_reason: str | None = None

    @field_validator("sequence")
    @classmethod
    def _normalize_sequence(cls, value: str, info: ValidationInfo) -> str:
        return normalize_sequence_field(value, info)

    @field_validator("structure_path")
    @classmethod
    def _check_structure_path(cls, value: Path | None) -> Path | None:
        return validate_structure_path(value)
