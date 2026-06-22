"""The committed demos/ manifests load, honor the license gate, and pin their slices.

This validates the real manifest files (not synthetic fixtures): each parses, only
redistributable datasets commit a slice, and every committed slice file matches the
sha256 the manifest pins (so vendored bytes can never drift unnoticed). It does NOT
fetch upstream data or run audits.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from veritas.demos.fetch import verify_file
from veritas.demos.manifest import load_manifest

_DEMOS = Path(__file__).resolve().parents[2] / "demos"
_MANIFESTS = sorted(_DEMOS.glob("*/manifest.toml"))


def test_demos_directory_has_manifests() -> None:
    assert _MANIFESTS, "no demos/*/manifest.toml files found"


@pytest.mark.parametrize("path", _MANIFESTS, ids=lambda p: p.parent.name)
def test_each_manifest_loads_and_honors_the_license_gate(path: Path) -> None:
    manifest = load_manifest(path)
    assert manifest.name and manifest.license and manifest.slice_spec
    if manifest.slice_files:
        assert manifest.redistributable, (
            f"{manifest.name} commits a slice but is not redistributable"
        )


@pytest.mark.parametrize("path", _MANIFESTS, ids=lambda p: p.parent.name)
def test_committed_slice_files_match_their_pinned_hashes(path: Path) -> None:
    manifest = load_manifest(path)
    for slice_file in manifest.slice_files:
        target = path.parent / slice_file.path
        assert target.exists(), f"committed slice file missing: {target}"
        verify_file(target, slice_file.sha256)  # raises ChecksumMismatchError on drift
