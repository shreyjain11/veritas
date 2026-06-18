"""Canonical JSON: sorted, compact, key-order-independent, idempotent (property-based)."""

from __future__ import annotations

import json
import random
from typing import Any

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from veritas.provenance import canonical_json

_json_scalars = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text()
)
_json_values = st.recursive(
    _json_scalars,
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=20,
)


def test_canonical_json_sorts_keys() -> None:
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_canonical_json_is_compact() -> None:
    assert canonical_json([1, 2]) == "[1,2]"


def test_key_insertion_order_does_not_matter() -> None:
    assert canonical_json({"a": 1, "b": 2}) == canonical_json({"b": 2, "a": 1})


@example(-0.0)  # pin: negative zero must canonicalize stably
@given(_json_values)
def test_canonical_is_idempotent(value: object) -> None:
    once = canonical_json(value)
    assert canonical_json(json.loads(once)) == once


# --- Recursive key-permutation invariance ----------------------------------
#
# audit_hash determinism depends on canonical_json producing the SAME bytes no
# matter what order dicts were constructed in -- at every nesting level. The
# idempotence property above cannot catch a "sorts top-level keys only" bug: a
# json round-trip preserves the buggy nested order, so re-serializing reproduces
# the same (wrong) string. Recursively permuting keys does catch it.

_permutable_values = st.recursive(
    _json_scalars,
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(st.text(min_size=1, max_size=4), children, max_size=4)
    ),
    max_leaves=15,
)


def _permute_keys(value: Any, rng: random.Random) -> Any:
    """Recursively reorder dict items at every nesting level; values unchanged."""
    if isinstance(value, dict):
        items = list(value.items())
        rng.shuffle(items)
        return {key: _permute_keys(item, rng) for key, item in items}
    if isinstance(value, list):
        return [_permute_keys(item, rng) for item in value]
    return value


# pin: a deeply-nested dict whose keys are out of sorted order at every level
@example(
    value={"b": {"d": 1, "a": {"z": 0, "k": [{"y": 1, "x": 2}]}}, "a": 3},
    permutation_seed=12345,
)
@given(
    value=st.dictionaries(
        st.text(min_size=1, max_size=4), _permutable_values, min_size=2, max_size=5
    ),
    permutation_seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_canonical_is_invariant_under_recursive_key_permutation(
    value: dict[str, Any], permutation_seed: int
) -> None:
    permuted = _permute_keys(value, random.Random(permutation_seed))
    assert permuted == value  # same content; only dict insertion order differs
    assert canonical_json(value) == canonical_json(permuted)


# --- Float canonicalization stress -----------------------------------------


def test_negative_zero_canonicalizes_like_zero() -> None:
    assert canonical_json({"x": -0.0}) == canonical_json({"x": 0.0})


def test_high_precision_float_repr_is_preserved() -> None:
    # full shortest-round-trip repr, not a truncated/rounded form
    assert canonical_json({"x": 0.1 + 0.2}) == '{"x":0.30000000000000004}'


def test_large_and_small_magnitudes_round_trip_stably() -> None:
    for value in (1e300, 1e-300):
        once = canonical_json({"x": value})
        assert canonical_json(json.loads(once)) == once


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_floats_are_rejected(bad: float) -> None:
    # Non-finite values must never silently enter a provenance artifact.
    with pytest.raises(ValueError):
        canonical_json({"x": bad})
