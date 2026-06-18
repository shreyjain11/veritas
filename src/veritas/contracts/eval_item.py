"""EvalItem: one evaluation example (sequence + label + optional prediction/structure)."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, ValidationInfo, field_validator

from veritas.contracts.base import FrozenModel
from veritas.contracts.enums import SeqType
from veritas.contracts.sequences import normalize_sequence_field
from veritas.contracts.structure import validate_structure_path


class EvalItem(FrozenModel):
    id: str = Field(min_length=1)
    seq_type: SeqType
    sequence: str = Field(min_length=1)
    label: float
    # Scalar in v1 (binary score / regression / ranking); kept widenable so a
    # vector prediction is a non-breaking addition later (docs/PLAN.md decision #9).
    prediction: float | None = None
    # Optional structure for structural contamination detection (foldseek);
    # mirrors ReferenceItem.structure_path (added for Phase 2's structural detector).
    structure_path: Path | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @field_validator("sequence")
    @classmethod
    def _normalize_sequence(cls, value: str, info: ValidationInfo) -> str:
        return normalize_sequence_field(value, info)

    @field_validator("structure_path")
    @classmethod
    def _check_structure_path(cls, value: Path | None) -> Path | None:
        return validate_structure_path(value)
