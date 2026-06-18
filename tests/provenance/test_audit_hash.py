"""Stable audit hash: deterministic, timestamp-independent, sensitive to inputs."""

from __future__ import annotations

from veritas.contracts import ProvenanceRecord
from veritas.provenance import audit_hash


def _record(
    seed: int = 1,
    params: dict[str, object] | None = None,
    created_at: str | None = None,
) -> ProvenanceRecord:
    return ProvenanceRecord(
        input_hashes={"benchmark": "abc"},
        params=params if params is not None else {"seed": seed},
        seed=seed,
        pinned_versions={"mmseqs": "18.8cc5c"},
        runtime_versions={"mmseqs": "18.8cc5c"},
        created_at=created_at,
    )


def test_audit_hash_is_deterministic() -> None:
    assert audit_hash(_record()) == audit_hash(_record())


def test_audit_hash_ignores_timestamp() -> None:
    early = _record(created_at="2026-01-01T00:00:00Z")
    late = _record(created_at="2030-12-31T23:59:59Z")
    assert audit_hash(early) == audit_hash(late)


def test_audit_hash_changes_with_seed() -> None:
    assert audit_hash(_record(seed=1)) != audit_hash(_record(seed=2))


def test_audit_hash_changes_with_params() -> None:
    assert audit_hash(_record(params={"deleak": "drop"})) != audit_hash(
        _record(params={"deleak": "reweight"})
    )
