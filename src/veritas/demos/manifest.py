"""Dataset manifest: pins upstream + vendored-slice checksums and the license gate.

A manifest is the single declaration for a demo/repro dataset: where the upstream
data lives (URL + sha256), which curated slice files are vendored (path + sha256),
and whether the license permits committing that slice (``redistributable`` -- an
explicit decision, never a default). The slice hashes are namespaced so they can be
merged straight into an audit's ``provenance.input_hashes`` (byte-exact pinning).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator

from veritas.contracts.base import FrozenModel

#: A lowercase-hex sha256 digest.
_SHA256 = r"^[0-9a-f]{64}$"


class DataSource(FrozenModel):
    url: str = Field(min_length=1)
    # Pinned upstream digest. ``None`` = not yet materialized/pinned; fetch refuses to
    # download an unpinned source (no trust-on-first-use).
    sha256: str | None = Field(default=None, pattern=_SHA256)
    role: str = "archive"


class SliceFile(FrozenModel):
    path: str = Field(min_length=1)
    # A committed slice file is always pinned (it is in the repo, byte-exact).
    sha256: str = Field(pattern=_SHA256)


class DatasetManifest(FrozenModel):
    name: str = Field(min_length=1)
    license: str = Field(min_length=1)
    # Hard license gate: may the curated slice be committed to the repo? Mandatory
    # (no default) -- redistributability must be an explicit, reviewed decision.
    redistributable: bool
    # What slice to materialize from the upstream sources (always documented, even when
    # the slice is fetch-only and never committed).
    slice_spec: str = Field(min_length=1)
    description: str = ""
    sources: tuple[DataSource, ...] = ()
    # Committed slice files (empty for fetch-only datasets).
    slice_files: tuple[SliceFile, ...] = ()

    @model_validator(mode="after")
    def _license_gate(self) -> Self:
        if not self.redistributable and self.slice_files:
            raise ValueError(
                "a non-redistributable dataset must not commit slice_files (fetch-only)"
            )
        return self

    def input_hashes(self) -> dict[str, str]:
        """Provenance-ready hashes for the vendored slice files, namespaced by dataset."""
        return {f"dataset:{self.name}:{f.path}": f.sha256 for f in self.slice_files}


def load_manifest(path: Path) -> DatasetManifest:
    return DatasetManifest.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
