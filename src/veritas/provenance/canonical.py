"""Canonical JSON serialization: the deterministic basis for all hashing.

Keys are sorted, output is compact, and floats use Python's shortest
round-tripping repr. ``-0.0`` is normalized to ``0.0`` so they serialize
identically, and non-finite floats (NaN, +/-inf) are rejected rather than
encoded — a non-finite value must never silently enter a provenance artifact
(docs/PLAN.md float-canonicalization requirements).
"""

from __future__ import annotations

import json
import math
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"non-finite float cannot be canonicalized: {value!r}")
        if value == 0.0:
            return 0.0  # collapse -0.0 to 0.0
        return value
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def canonical_json(obj: Any) -> str:
    return json.dumps(
        _normalize(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def canonical_bytes(obj: Any) -> bytes:
    return canonical_json(obj).encode("utf-8")
