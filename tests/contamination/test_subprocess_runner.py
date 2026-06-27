"""Sandboxed subprocess runner (security boundary, docs/SPEC.md §subprocess).

All commands run from an explicit argv list with no shell; arguments are never
shell-interpreted; inputs are validated; timeouts and nonzero exits are surfaced.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from veritas.contamination.subprocess_runner import run_command


def test_runs_argv_and_captures_stdout(tmp_path: Path) -> None:
    result = run_command([sys.executable, "-c", "print('hello')"], cwd=tmp_path, timeout=30.0)
    assert result.returncode == 0
    assert result.stdout.strip() == "hello"


def test_arguments_are_not_shell_interpreted(tmp_path: Path) -> None:
    # If args were passed through a shell, this would attempt command substitution.
    dangerous = "$(touch pwned); rm -rf /"
    result = run_command(
        [sys.executable, "-c", "import sys; print(sys.argv[1])", dangerous],
        cwd=tmp_path,
        timeout=30.0,
    )
    assert result.stdout.strip() == dangerous
    assert not (tmp_path / "pwned").exists()


def test_never_invokes_a_shell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    real_run = subprocess.run

    def spy(*args: object, **kwargs: object) -> object:
        captured.update(kwargs)
        return real_run(*args, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr(subprocess, "run", spy)
    run_command([sys.executable, "-c", "pass"], cwd=tmp_path, timeout=30.0)
    assert captured.get("shell", False) is False


def test_timeout_is_enforced(tmp_path: Path) -> None:
    with pytest.raises(subprocess.TimeoutExpired):
        run_command([sys.executable, "-c", "import time; time.sleep(5)"], cwd=tmp_path, timeout=0.5)


def test_nonzero_exit_raises(tmp_path: Path) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        run_command([sys.executable, "-c", "import sys; sys.exit(3)"], cwd=tmp_path, timeout=30.0)


def test_rejects_empty_argv(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        run_command([], cwd=tmp_path, timeout=30.0)


def test_rejects_argv_with_null_byte(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        run_command([sys.executable, "bad\x00arg"], cwd=tmp_path, timeout=30.0)


def test_runs_in_provided_working_directory(tmp_path: Path) -> None:
    result = run_command(
        [sys.executable, "-c", "import os; print(os.getcwd())"], cwd=tmp_path, timeout=30.0
    )
    assert Path(result.stdout.strip()).resolve() == tmp_path.resolve()
