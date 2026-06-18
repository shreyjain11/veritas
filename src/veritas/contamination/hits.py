"""Raw backend-hit records shared by detectors and their parsers."""

from __future__ import annotations

from veritas.contracts.base import FrozenModel


class SequenceHit(FrozenModel):
    eval_id: str
    ref_id: str
    identity: float  # fractional identity, 0..1
    coverage: float  # fractional coverage, 0..1


class FamilyAssignment(FrozenModel):
    item_id: str
    family: str
    e_value: float


class StructuralHit(FrozenModel):
    eval_id: str
    ref_id: str
    tm_score: float  # 0..1
