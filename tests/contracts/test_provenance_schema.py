"""ProvenanceRecord schema: version slots, mismatch detection (req C), immutability."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veritas.contracts import ProvenanceRecord


def test_valid_provenance_record() -> None:
    rec = ProvenanceRecord(
        input_hashes={"benchmark": "abc"},
        params={"seed": 1},
        seed=1,
        pinned_versions={"mmseqs": "18.8cc5c"},
        runtime_versions={"mmseqs": "18.8cc5c"},
    )
    assert rec.seed == 1
    assert rec.input_hashes["benchmark"] == "abc"


def test_runtime_versions_default_empty() -> None:
    rec = ProvenanceRecord(
        input_hashes={},
        params={},
        seed=1,
        pinned_versions={"mmseqs": "18.8cc5c"},
    )
    assert rec.runtime_versions == {}


def test_version_mismatch_detected() -> None:
    rec = ProvenanceRecord(
        input_hashes={},
        params={},
        seed=1,
        pinned_versions={"mmseqs": "18.8cc5c"},
        runtime_versions={"mmseqs": "SOMETHING-ELSE"},
    )
    assert rec.version_mismatches == ("mmseqs",)


def test_no_mismatch_when_versions_equal() -> None:
    rec = ProvenanceRecord(
        input_hashes={},
        params={},
        seed=1,
        pinned_versions={"mmseqs": "18.8cc5c"},
        runtime_versions={"mmseqs": "18.8cc5c"},
    )
    assert rec.version_mismatches == ()


def test_is_frozen() -> None:
    rec = ProvenanceRecord(input_hashes={}, params={}, seed=1, pinned_versions={})
    with pytest.raises(ValidationError):
        rec.seed = 2


def test_round_trip_json() -> None:
    rec = ProvenanceRecord(
        input_hashes={"benchmark": "abc"},
        params={"seed": 1},
        seed=1,
        pinned_versions={"mmseqs": "18.8cc5c"},
        runtime_versions={"mmseqs": "18.8cc5c"},
    )
    assert ProvenanceRecord.model_validate_json(rec.model_dump_json()) == rec


def test_version_mismatch_only_for_tools_in_both_with_differing_values() -> None:
    rec = ProvenanceRecord(
        input_hashes={},
        params={},
        seed=1,
        pinned_versions={"mmseqs": "A", "foldseek": "X", "hmmer": "3.4"},
        runtime_versions={"mmseqs": "B", "foldseek": "X", "diamond": "2.2.1"},
    )
    # mmseqs: in both, differ -> mismatch.   foldseek: in both, equal -> not.
    # hmmer: pinned only (absent at runtime) -> not.  diamond: runtime only -> not.
    assert rec.version_mismatches == ("mmseqs",)


def test_version_mismatches_are_sorted() -> None:
    rec = ProvenanceRecord(
        input_hashes={},
        params={},
        seed=1,
        pinned_versions={"ztool": "1", "atool": "1"},
        runtime_versions={"ztool": "2", "atool": "2"},
    )
    assert rec.version_mismatches == ("atool", "ztool")
