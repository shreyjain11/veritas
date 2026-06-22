"""ProvenanceRecord assembly: inputs are content-hashed; versions captured."""

from __future__ import annotations

from veritas.provenance import build_provenance_record, content_hash


def test_build_record_captures_inputs_and_hashes() -> None:
    record = build_provenance_record(
        inputs={"benchmark": {"a": 1}, "config": {"seed": 1}},
        params={"seed": 1, "deleak": "drop"},
        seed=1,
        pinned_versions={"mmseqs": "18.8cc5c"},
        runtime_versions={"mmseqs": "18.8cc5c"},
    )
    assert record.seed == 1
    assert record.input_hashes["benchmark"] == content_hash({"a": 1})
    assert record.input_hashes["config"] == content_hash({"seed": 1})
    assert record.params["deleak"] == "drop"


def test_build_record_defaults_runtime_versions_empty() -> None:
    record = build_provenance_record(
        inputs={},
        params={},
        seed=7,
        pinned_versions={"mmseqs": "18.8cc5c"},
    )
    assert record.runtime_versions == {}


def test_extra_input_hashes_are_merged_verbatim_not_rehashed() -> None:
    # Vendored data-slice hashes are already sha256 of the file bytes; they must land
    # in input_hashes as-is, alongside the content-hashed in-memory inputs.
    slice_hash = "b" * 64
    record = build_provenance_record(
        inputs={"benchmark": {"a": 1}},
        params={},
        seed=1,
        pinned_versions={},
        extra_input_hashes={"dataset:demo:assay.csv": slice_hash},
    )
    assert record.input_hashes["benchmark"] == content_hash({"a": 1})
    assert record.input_hashes["dataset:demo:assay.csv"] == slice_hash
