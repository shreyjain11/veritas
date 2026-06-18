"""Runtime backend-version capture (req C), hermetic via an injected command runner."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from veritas.contamination.backends.diamond import DiamondSearch
from veritas.contamination.backends.foldseek import FoldseekSearch
from veritas.contamination.backends.mmseqs import MmseqsSearch
from veritas.contamination.backends.pyhmmer_search import PyhmmerSearch
from veritas.contamination.subprocess_runner import CommandResult, CommandRunner


def _fake_runner(stdout: str) -> CommandRunner:
    def runner(
        argv: Sequence[str], *, cwd: Path, timeout: float, input_text: str | None = None
    ) -> CommandResult:
        return CommandResult(stdout=stdout, stderr="", returncode=0)

    return runner


def test_mmseqs_version_is_captured() -> None:
    search = MmseqsSearch(runner=_fake_runner("MMseqs2 Version: 18.8cc5c"))
    assert "18.8cc5c" in search.version()


def test_foldseek_version_is_captured() -> None:
    search = FoldseekSearch(runner=_fake_runner("foldseek Version: 10.941cd33"))
    assert "10.941cd33" in search.version()


def test_diamond_version_is_captured() -> None:
    search = DiamondSearch(runner=_fake_runner("diamond version 2.2.1"))
    assert "2.2.1" in search.version()


def test_pyhmmer_version_is_reported() -> None:
    # pyhmmer is in-process; its version is read from the installed package.
    assert PyhmmerSearch().version()
