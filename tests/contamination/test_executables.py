"""Binary resolution: operator pin wins over PATH; absolute path used at exec."""

from __future__ import annotations

from pathlib import Path

import pytest

from veritas.contamination.backends.mmseqs import MmseqsSearch
from veritas.contamination.executables import env_var_for, resolve_executable
from veritas.contamination.subprocess_runner import CommandResult


def test_env_var_naming() -> None:
    assert env_var_for("mmseqs") == "VERITAS_MMSEQS_BIN"


def test_resolve_prefers_the_operator_pin_over_path() -> None:
    env = {"VERITAS_MMSEQS_BIN": "/opt/pinned/mmseqs"}
    assert resolve_executable("mmseqs", environ=env) == "/opt/pinned/mmseqs"


def test_resolve_falls_back_to_path(tmp_path: Path) -> None:
    exe = tmp_path / "mytool"
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)
    env = {"PATH": str(tmp_path)}
    assert resolve_executable("mytool", environ=env) == str(exe)


def test_resolve_returns_none_when_absent() -> None:
    assert resolve_executable("definitely-not-a-real-tool-xyz", environ={"PATH": ""}) is None


def test_backend_resolves_at_init_and_runs_the_absolute_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Resolution happens once at construction; the stored absolute path (not the bare
    # name) is what gets executed -- so a later PATH change cannot redirect the call.
    monkeypatch.setenv("VERITAS_MMSEQS_BIN", "/opt/pinned/mmseqs")
    captured: dict[str, list[str]] = {}

    def fake_runner(argv, *, cwd, timeout, input_text=None):  # type: ignore[no-untyped-def]
        captured["argv"] = list(argv)
        return CommandResult(stdout="v", stderr="", returncode=0)

    search = MmseqsSearch(runner=fake_runner)
    assert search.binary_path == "/opt/pinned/mmseqs"
    search.version()
    assert captured["argv"][0] == "/opt/pinned/mmseqs"
