"""Tamper-evident hashing for schema-v2 reports.

The ``audit_hash`` of a v2 report is the SHA-256 of the canonical JSON of the *whole*
report except the ``audit_hash`` field itself, so editing any score, finding,
response, or provenance value is detectable.

The canonical form is designed to be reproducible outside Python (the web viewer
re-derives it in TypeScript): object keys sorted, compact separators, ASCII-only
escaping, integer-valued floats written as integers (``1.0`` -> ``1``, because a
JSON round-trip through JavaScript cannot tell them apart), and other floats in
Python's shortest round-trip ``repr`` (``1e-07``, ``0.25``).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any


def canonicalize(value: Any) -> Any:
    """Normalize a JSON-compatible value into its hash-canonical shape."""
    if isinstance(value, bool) or value is None or isinstance(value, str | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numbers cannot appear in a hashed report")
        return int(value) if value.is_integer() else value
    if isinstance(value, Mapping):
        return {str(key): canonicalize(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [canonicalize(item) for item in value]
    raise TypeError(f"cannot canonicalize value of type {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def report_hash(report: Mapping[str, Any]) -> str:
    """The audit hash for a report dict (its own ``audit_hash`` field is ignored)."""
    return sha256_json({key: value for key, value in report.items() if key != "audit_hash"})


def verify_report_hash(report: Mapping[str, Any]) -> tuple[bool, str, str]:
    """Return ``(matches, computed, stored)`` for a parsed schema-v2 report."""
    stored = str(report.get("audit_hash", ""))
    computed = report_hash(report)
    return computed == stored, computed, stored
