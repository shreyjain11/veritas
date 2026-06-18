"""PredictionRecord / PredictionSet: id alignment, uniqueness, immutability."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veritas.contracts import PredictionRecord, PredictionSet


def test_prediction_record_valid() -> None:
    rec = PredictionRecord(item_id="e1", value=0.7)
    assert rec.item_id == "e1"
    assert rec.value == 0.7


def test_prediction_set_as_mapping() -> None:
    ps = PredictionSet(
        records=(
            PredictionRecord(item_id="e1", value=0.1),
            PredictionRecord(item_id="e2", value=0.2),
        )
    )
    assert ps.as_mapping() == {"e1": 0.1, "e2": 0.2}


def test_prediction_set_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError):
        PredictionSet(
            records=(
                PredictionRecord(item_id="e1", value=0.1),
                PredictionRecord(item_id="e1", value=0.2),
            )
        )


def test_prediction_set_is_frozen() -> None:
    ps = PredictionSet(records=(PredictionRecord(item_id="e1", value=0.1),))
    with pytest.raises(ValidationError):
        ps.records = ()


def test_round_trip_json() -> None:
    ps = PredictionSet(records=(PredictionRecord(item_id="e1", value=0.1),))
    assert PredictionSet.model_validate_json(ps.model_dump_json()) == ps
