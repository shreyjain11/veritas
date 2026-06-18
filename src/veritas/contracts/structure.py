"""Shared validation for optional structure-file paths (PDB/mmCIF)."""

from __future__ import annotations

from pathlib import Path

STRUCTURE_SUFFIXES = frozenset({".pdb", ".cif", ".mmcif", ".ent"})


def validate_structure_path(value: Path | None) -> Path | None:
    if value is None:
        return value
    if value.suffix.lower() not in STRUCTURE_SUFFIXES:
        raise ValueError(
            f"structure_path must be one of {sorted(STRUCTURE_SUFFIXES)}; got {value.suffix!r}"
        )
    return value
