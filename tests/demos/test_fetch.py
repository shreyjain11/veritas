"""Fetching is fail-loud at every checksum: upstream archive AND extracted slice.

A corrupted download or a tampered slice must raise, never silently proceed -- the
whole point of vendoring is byte-exact reproducibility. The downloader is injected so
these tests never touch the network; the default downloader enforces HTTPS.
"""

from __future__ import annotations

import hashlib
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from veritas.demos.fetch import ChecksumMismatchError, fetch_dataset, verify_file
from veritas.demos.manifest import DatasetManifest


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _zip_with(tmp_path: Path, members: dict[str, bytes]) -> Path:
    archive = tmp_path / "src.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return archive


def _manifest(
    archive: Path, archive_sha: str, slice_files: list[dict[str, str]]
) -> DatasetManifest:
    return DatasetManifest.model_validate(
        {
            "name": "demo",
            "license": "MIT",
            "redistributable": True,
            "slice_spec": "demo slice",
            "sources": [
                {
                    "url": f"https://example.org/{archive.name}",
                    "sha256": archive_sha,
                    "role": "archive",
                }
            ],
            "slice_files": slice_files,
        }
    )


def _copy_downloader(archive: Path) -> Callable[[str, Path], None]:
    def downloader(url: str, target: Path) -> None:  # fake "download": copy the local archive
        target.write_bytes(archive.read_bytes())

    return downloader


def test_verify_file_passes_on_match(tmp_path: Path) -> None:
    f = tmp_path / "x"
    f.write_bytes(b"hello")
    verify_file(f, _sha256(b"hello"))  # no raise


def test_verify_file_fails_loud_on_mismatch(tmp_path: Path) -> None:
    f = tmp_path / "x"
    f.write_bytes(b"hello")
    with pytest.raises(ChecksumMismatchError):
        verify_file(f, "0" * 64)


def test_fetch_downloads_verifies_extracts_then_verifies_slice(tmp_path: Path) -> None:
    content = b"id,label\n1,0\n"
    archive = _zip_with(tmp_path, {"assay.csv": content})
    manifest = _manifest(
        archive, _sha256(archive.read_bytes()), [{"path": "assay.csv", "sha256": _sha256(content)}]
    )
    dest = tmp_path / "out"
    fetch_dataset(manifest, dest, downloader=_copy_downloader(archive))
    assert (dest / "assay.csv").read_bytes() == content


def test_fetch_fails_loud_on_corrupted_download(tmp_path: Path) -> None:
    archive = _zip_with(tmp_path, {"assay.csv": b"x"})
    manifest = _manifest(archive, "0" * 64, [{"path": "assay.csv", "sha256": _sha256(b"x")}])
    with pytest.raises(ChecksumMismatchError):
        fetch_dataset(manifest, tmp_path / "out", downloader=_copy_downloader(archive))


def test_fetch_fails_loud_on_slice_mismatch(tmp_path: Path) -> None:
    content = b"real"
    archive = _zip_with(tmp_path, {"assay.csv": content})
    manifest = _manifest(
        archive, _sha256(archive.read_bytes()), [{"path": "assay.csv", "sha256": "0" * 64}]
    )
    with pytest.raises(ChecksumMismatchError):
        fetch_dataset(manifest, tmp_path / "out", downloader=_copy_downloader(archive))


def test_fetch_reports_a_missing_slice_member(tmp_path: Path) -> None:
    archive = _zip_with(tmp_path, {"other.csv": b"x"})  # archive lacks the declared slice file
    manifest = _manifest(
        archive, _sha256(archive.read_bytes()), [{"path": "assay.csv", "sha256": _sha256(b"x")}]
    )
    with pytest.raises(FileNotFoundError, match=r"assay\.csv"):
        fetch_dataset(manifest, tmp_path / "out", downloader=_copy_downloader(archive))


def test_fetch_supports_a_non_archive_single_file_source(tmp_path: Path) -> None:
    # A source that is the slice file itself (no .zip): downloaded, verified, no extraction.
    content = b"id,label\n1,0\n"
    source = tmp_path / "assay.csv"
    source.write_bytes(content)
    manifest = DatasetManifest.model_validate(
        {
            "name": "demo",
            "license": "MIT",
            "redistributable": True,
            "slice_spec": "single csv",
            "sources": [{"url": "https://example.org/assay.csv", "sha256": _sha256(content)}],
            "slice_files": [{"path": "assay.csv", "sha256": _sha256(content)}],
        }
    )
    dest = tmp_path / "out"
    fetch_dataset(manifest, dest, downloader=_copy_downloader(source))
    assert (dest / "assay.csv").read_bytes() == content


def test_fetch_refuses_an_unpinned_source(tmp_path: Path) -> None:
    # A source with no sha256 is unpinned -> fetch must refuse (no trust-on-first-use).
    content = b"x"
    archive = _zip_with(tmp_path, {"a.csv": content})
    manifest = DatasetManifest.model_validate(
        {
            "name": "demo",
            "license": "MIT",
            "redistributable": True,
            "slice_spec": "s",
            "sources": [{"url": f"https://example.org/{archive.name}"}],  # no sha256
            "slice_files": [{"path": "a.csv", "sha256": _sha256(content)}],
        }
    )
    with pytest.raises(ValueError, match="not pinned"):
        fetch_dataset(manifest, tmp_path / "out", downloader=_copy_downloader(archive))


def test_default_downloader_rejects_non_https(tmp_path: Path) -> None:
    content = b"x"
    archive = _zip_with(tmp_path, {"a.csv": content})
    manifest = DatasetManifest.model_validate(
        {
            "name": "demo",
            "license": "MIT",
            "redistributable": True,
            "slice_spec": "s",
            "sources": [
                {
                    "url": f"http://example.org/{archive.name}",
                    "sha256": _sha256(archive.read_bytes()),
                }
            ],
            "slice_files": [{"path": "a.csv", "sha256": _sha256(content)}],
        }
    )
    with pytest.raises(ValueError, match="https"):
        fetch_dataset(manifest, tmp_path / "out")  # default downloader enforces https, no network
