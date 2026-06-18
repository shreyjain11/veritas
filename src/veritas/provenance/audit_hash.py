"""Stable audit hash over a ProvenanceRecord (excluding the wall-clock stamp)."""

from __future__ import annotations

from veritas.contracts import ProvenanceRecord
from veritas.provenance.hashing import content_hash


def audit_hash(record: ProvenanceRecord) -> str:
    """Hash the deterministic content of a record.

    ``created_at`` is intentionally excluded so two runs with identical inputs
    and seed produce an identical hash (determinism).
    """
    payload = {
        "input_hashes": record.input_hashes,
        "params": record.params,
        "seed": record.seed,
        "pinned_versions": record.pinned_versions,
        "runtime_versions": record.runtime_versions,
    }
    return content_hash(payload)
