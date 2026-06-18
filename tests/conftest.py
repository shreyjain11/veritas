"""Shared pytest fixtures and configuration for the Veritas suite.

Phase 0: minimal scaffold plus a hermeticity safety net. Later phases grow this
with seeded synthetic-dataset factories and binary-availability skip logic
(docs/PLAN.md §0).
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator

import pytest
from hypothesis import settings
from pytest_socket import disable_socket, enable_socket

#: Canonical deterministic seed used across the suite (docs/PLAN.md: determinism).
DEFAULT_SEED = 1729

# Hypothesis example budgets. The default ("dev") keeps local runs fast; CI opts into
# a higher budget via HYPOTHESIS_PROFILE=ci so the rare-but-critical inputs in the
# differential and idempotence properties get far more search. Selected per-test
# @settings (e.g. the LSH-index-building near-dup test) still override these.
settings.register_profile("dev", max_examples=100)
settings.register_profile("ci", max_examples=1000, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))

# Binary-backed tests (golden end-to-end + differential) auto-skip when the
# pinned tool is not on PATH, so the hermetic core suite stays green offline;
# CI installs the pinned binaries via micromamba and runs them for real.
_BINARY_FOR_MARKER = {
    "requires_mmseqs": "mmseqs",
    "requires_diamond": "diamond",
    "requires_foldseek": "foldseek",
    "requires_hmmer": "hmmsearch",
}


def pytest_runtest_setup(item: pytest.Item) -> None:
    for marker in item.iter_markers():
        binary = _BINARY_FOR_MARKER.get(marker.name)
        if binary is not None and shutil.which(binary) is None:
            pytest.skip(f"{binary} not available on PATH")


# Tests carrying one of these markers are allowed real network access; every
# other ("core") test runs with sockets blocked so an accidental network call
# fails loudly even on a local run without the CLI ``--disable-socket`` flag
# (docs/PLAN.md decision #20: the core suite is hermetic/offline).
_NETWORK_ALLOWED_MARKERS = ("external", "scale", "requires_pfam")


@pytest.fixture(autouse=True)
def _hermetic_network(request: pytest.FixtureRequest) -> Iterator[None]:
    allows_network = any(
        request.node.get_closest_marker(marker) for marker in _NETWORK_ALLOWED_MARKERS
    )
    if allows_network:
        enable_socket()
    else:
        # Block real (AF_INET) network but allow AF_UNIX socketpairs: asyncio's event
        # loop self-pipe and the in-memory MCP transport are local IPC, not network.
        disable_socket(allow_unix_socket=True)
    try:
        yield
    finally:
        disable_socket(allow_unix_socket=True)


@pytest.fixture
def seed() -> int:
    """Return the canonical deterministic seed for tests that need one."""
    return DEFAULT_SEED
