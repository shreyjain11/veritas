"""Content hashing: sha256 over the canonical form of an object or file."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from veritas.provenance.canonical import canonical_bytes


def content_hash(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
