"""Phase 5 report-renderer tests."""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def golden(name: str) -> str:
    """Read a committed golden artifact (generated and locked during GREEN)."""
    return (FIXTURES / name).read_text(encoding="utf-8")
