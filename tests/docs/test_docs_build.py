"""The docs site builds cleanly, and the limitations page stays honest.

`mkdocs build --strict` turns broken nav/links into failures, so a green build
proves the site is internally consistent. mkdocs is the optional ``docs`` extra,
so that test skips when it is not installed. The honesty checks read the Markdown
directly (no mkdocs needed) and assert the *measured* figures from
``veritas.report.limitations`` actually appear on the limitations page -- so the
docs cannot silently drift from the numbers the code discloses.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from veritas.report.limitations import BOOTSTRAP_SMALL_N, MINHASH_NONCONSERVATIVE

REPO_ROOT = Path(__file__).resolve().parents[2]
LIMITATIONS_PAGE = REPO_ROOT / "docs" / "limitations-and-guarantees.md"
VALIDATION_PAGE = REPO_ROOT / "docs" / "validation.md"


def test_docs_build_is_strict(tmp_path: Path) -> None:
    pytest.importorskip("mkdocs")
    result = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "--site-dir", str(tmp_path / "site")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_limitations_page_states_the_measured_figures() -> None:
    text = LIMITATIONS_PAGE.read_text(encoding="utf-8")
    # The exact measured numbers the code discloses must appear verbatim.
    for figure in ("0.927", "n=25", "56%"):
        assert figure in text, f"limitations page is missing the measured figure {figure!r}"
    # ...and they must match the figures baked into the limitations module.
    assert "0.927" in BOOTSTRAP_SMALL_N.detail and "n=25" in BOOTSTRAP_SMALL_N.detail
    assert "56%" in MINHASH_NONCONSERVATIVE.detail


def test_limitations_page_states_the_guarantees() -> None:
    text = LIMITATIONS_PAGE.read_text(encoding="utf-8").lower()
    for term in ("provenance", "determinism", "audit_hash", "model-agnostic"):
        assert term.lower() in text, f"limitations page is missing the guarantee term {term!r}"


def test_validation_page_marks_demos_in_progress_without_results() -> None:
    text = VALIDATION_PAGE.read_text(encoding="utf-8").lower()
    assert "in progress" in text
    assert "no fabricated results" in text or "no demonstration" in text
