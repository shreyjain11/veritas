"""End-to-end, demonstration, and external-reproduction tests."""

from __future__ import annotations

import os

import pytest


def demo_data_or_skip(name: str) -> str:
    """Return the demo-data root, or skip (data is fetched only in the opt-in job)."""
    root = os.environ.get("VERITAS_DEMO_DATA", "")
    if not root:
        pytest.skip(f"demo/repro data for {name!r} unavailable (set VERITAS_DEMO_DATA; opt-in)")
    return root
