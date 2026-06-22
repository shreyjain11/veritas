"""Assemble a ProvenanceRecord, content-hashing each declared input."""

from __future__ import annotations

from typing import Any

from veritas.contracts import ProvenanceRecord
from veritas.provenance.hashing import content_hash


def build_provenance_record(
    *,
    inputs: dict[str, Any],
    params: dict[str, Any],
    seed: int,
    pinned_versions: dict[str, str],
    runtime_versions: dict[str, str] | None = None,
    extra_input_hashes: dict[str, str] | None = None,
) -> ProvenanceRecord:
    # In-memory inputs are content-hashed; extra_input_hashes are already file digests
    # (e.g. vendored data-slice sha256s) and are merged verbatim.
    input_hashes = {name: content_hash(value) for name, value in inputs.items()}
    if extra_input_hashes:
        input_hashes.update(extra_input_hashes)
    return ProvenanceRecord(
        input_hashes=input_hashes,
        params=params,
        seed=seed,
        pinned_versions=pinned_versions,
        runtime_versions=runtime_versions or {},
    )
