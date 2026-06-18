"""Content hashing: sha256 over the canonical form, cross-checked against stdlib.

Ground truth is the *hand-specified* canonical byte string hashed with hashlib —
not the implementation hashing itself — so this pins both canonicalization and
the digest (CLAUDE.md: never assert a fabricated expected value).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from veritas.provenance import content_hash, hash_file


def test_content_hash_is_sha256_of_canonical_form() -> None:
    expected = hashlib.sha256(b'{"a":1,"b":2}').hexdigest()
    assert content_hash({"b": 2, "a": 1}) == expected


def test_content_hash_of_string() -> None:
    expected = hashlib.sha256(b'"ACGT"').hexdigest()
    assert content_hash("ACGT") == expected


def test_content_hash_of_float_is_stable() -> None:
    expected = hashlib.sha256(b'{"x":0.5}').hexdigest()
    assert content_hash({"x": 0.5}) == expected


def test_key_order_does_not_change_hash() -> None:
    assert content_hash({"a": 1, "b": 2}) == content_hash({"b": 2, "a": 1})


def test_one_byte_change_changes_hash() -> None:
    assert content_hash({"x": 0.5}) != content_hash({"x": 0.6})


def test_hash_file_is_sha256_of_bytes(tmp_path: Path) -> None:
    path = tmp_path / "f.bin"
    path.write_bytes(b"ACGT\n")
    assert hash_file(path) == hashlib.sha256(b"ACGT\n").hexdigest()


# --- Float canonicalization stress -----------------------------------------


def test_negative_zero_hashes_like_zero() -> None:
    assert content_hash({"x": -0.0}) == content_hash({"x": 0.0})


def test_high_precision_float_hash_is_full_precision() -> None:
    expected = hashlib.sha256(b'{"x":0.30000000000000004}').hexdigest()
    assert content_hash({"x": 0.1 + 0.2}) == expected


def test_large_magnitude_hash_is_stable() -> None:
    expected = hashlib.sha256(b'{"x":1e+300}').hexdigest()
    assert content_hash({"x": 1e300}) == expected


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_floats_are_rejected_by_content_hash(bad: float) -> None:
    with pytest.raises(ValueError):
        content_hash({"x": bad})
