"""Dataset manifest schema: pins upstream + vendored-slice checksums and the license gate.

A manifest declares where the upstream data lives (URL + sha256), which curated slice
files are vendored (path + sha256), and -- critically -- whether the dataset's license
permits committing that slice (``redistributable``). The slice hashes are namespaced so
they can be merged straight into an audit's provenance.input_hashes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from veritas.demos.manifest import DatasetManifest, load_manifest

_HEX = "a" * 64

_VENDORED = f"""
name = "proteingym_dms"
description = "ProteinGym DMS substitutions (curated slice)"
license = "ProteinGym (MIT)"
redistributable = true
slice_spec = "one assay CSV per MSA-depth category + its reference rows"

[[sources]]
url = "https://example.org/data.zip"
sha256 = "{_HEX}"
role = "archive"

[[slice_files]]
path = "assay_low.csv"
sha256 = "{_HEX}"
"""

# Fetch-only: not redistributable, so NO committed slice, and the upstream source's
# checksum is not pinned until someone materializes it.
_FETCH_ONLY = """
name = "loco_epi"
license = "no license file (all rights reserved)"
redistributable = false
slice_spec = "INPUT_DATA enhancer/promoter pairs + chromosome folds"

[[sources]]
url = "https://example.org/repo"
role = "repo"
"""


def test_load_vendored_manifest_parses_all_fields(tmp_path: Path) -> None:
    path = tmp_path / "manifest.toml"
    path.write_text(_VENDORED, encoding="utf-8")
    manifest = load_manifest(path)
    assert manifest.name == "proteingym_dms"
    assert manifest.redistributable is True
    assert manifest.slice_spec
    assert manifest.sources[0].sha256 == _HEX
    assert manifest.slice_files[0].path == "assay_low.csv"


def test_input_hashes_are_namespaced_by_dataset_and_path(tmp_path: Path) -> None:
    path = tmp_path / "manifest.toml"
    path.write_text(_VENDORED, encoding="utf-8")
    manifest = load_manifest(path)
    assert manifest.input_hashes() == {"dataset:proteingym_dms:assay_low.csv": _HEX}


def test_fetch_only_manifest_has_no_committed_slice(tmp_path: Path) -> None:
    path = tmp_path / "manifest.toml"
    path.write_text(_FETCH_ONLY, encoding="utf-8")
    manifest = load_manifest(path)
    assert manifest.redistributable is False
    assert manifest.slice_files == ()
    assert manifest.input_hashes() == {}  # nothing committed to pin
    assert manifest.sources[0].sha256 is None  # unpinned until materialized


def test_non_redistributable_cannot_commit_a_slice() -> None:
    # The license gate is enforced: a non-redistributable dataset must not vendor a slice.
    with pytest.raises(ValueError, match="redistributable"):
        DatasetManifest.model_validate(
            {
                "name": "x",
                "license": "proprietary",
                "redistributable": False,
                "slice_spec": "s",
                "slice_files": [{"path": "a", "sha256": _HEX}],
            }
        )


def test_bad_sha256_length_is_rejected() -> None:
    with pytest.raises(ValueError):
        DatasetManifest.model_validate(
            {
                "name": "x",
                "license": "MIT",
                "redistributable": True,
                "slice_spec": "s",
                "slice_files": [{"path": "a", "sha256": "tooshort"}],
            }
        )


def test_slice_spec_is_mandatory() -> None:
    with pytest.raises(ValueError):
        DatasetManifest.model_validate({"name": "x", "license": "MIT", "redistributable": False})


def test_redistributable_flag_is_mandatory() -> None:
    # The license gate must be an explicit decision, never an implicit default.
    with pytest.raises(ValueError):
        DatasetManifest.model_validate({"name": "x", "license": "MIT", "slice_spec": "s"})
