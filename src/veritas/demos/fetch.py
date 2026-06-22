"""Fail-loud fetching of a vendored dataset slice.

The flow is: download each upstream source -> verify its sha256 -> extract the
declared slice members -> verify each slice file's sha256. A mismatch at ANY step
raises ``ChecksumMismatchError`` and nothing downstream is trusted -- byte-exact
reproducibility is the entire point. The downloader is injectable so tests never
touch the network; the default downloader enforces HTTPS.
"""

from __future__ import annotations

import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

from veritas.demos.manifest import DatasetManifest
from veritas.provenance.hashing import hash_file

#: ``(url, dest)`` -> writes the downloaded bytes to ``dest``.
Downloader = Callable[[str, Path], None]


class ChecksumMismatchError(RuntimeError):
    """A file's sha256 did not match the manifest (fail loud; never proceed)."""


def verify_file(path: Path, expected_sha256: str) -> None:
    actual = hash_file(path)
    if actual != expected_sha256:
        raise ChecksumMismatchError(f"{path}: expected sha256 {expected_sha256}, got {actual}")


def _https_download(url: str, dest: Path) -> None:
    if not url.startswith("https://"):
        raise ValueError(f"refusing non-https source url: {url!r}")
    with urllib.request.urlopen(url) as response:  # pragma: no cover - network
        dest.write_bytes(response.read())  # pragma: no cover - network


def fetch_dataset(
    manifest: DatasetManifest, dest_root: Path, *, downloader: Downloader = _https_download
) -> Path:
    """Fetch + checksum-verify ``manifest``'s data into ``dest_root``; return that root."""
    dest_root.mkdir(parents=True, exist_ok=True)
    wanted = {slice_file.path for slice_file in manifest.slice_files}
    for source in manifest.sources:
        if source.sha256 is None:
            raise ValueError(
                f"source {source.url!r} is not pinned (no sha256); pin it before fetch"
            )
        archive = dest_root / Path(source.url).name
        downloader(source.url, archive)
        verify_file(archive, source.sha256)  # fail loud on a corrupted/tampered download
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as zf:
                for member in zf.namelist():
                    if member in wanted:
                        zf.extract(member, dest_root)
    for slice_file in manifest.slice_files:
        target = dest_root / slice_file.path
        if not target.exists():
            raise FileNotFoundError(f"slice file {slice_file.path!r} missing after fetch")
        verify_file(target, slice_file.sha256)  # fail loud on a tampered slice
    return dest_root
