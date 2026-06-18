"""PredictionRecord / PredictionSet: a model's per-example predictions, id-aligned."""

from __future__ import annotations

from pydantic import field_validator

from veritas.contracts.base import FrozenModel


class PredictionRecord(FrozenModel):
    item_id: str
    value: float


class PredictionSet(FrozenModel):
    records: tuple[PredictionRecord, ...]

    @field_validator("records")
    @classmethod
    def _ids_unique(cls, value: tuple[PredictionRecord, ...]) -> tuple[PredictionRecord, ...]:
        ids = [record.item_id for record in value]
        if len(ids) != len(set(ids)):
            raise ValueError("PredictionSet contains duplicate item_id values")
        return value

    def as_mapping(self) -> dict[str, float]:
        return {record.item_id: record.value for record in self.records}
