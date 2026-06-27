"""Sandboxed subprocess execution for the binary-backed detectors.

The single choke point through which mmseqs / diamond / foldseek (and any HMMER
binary used in differential tests) are invoked. Hardening rules (docs/SPEC.md
§subprocess): commands are an explicit argv list run with ``shell=False`` (so
arguments are never shell-interpreted), inputs are validated, every call runs in
a caller-provided working directory, and timeouts / nonzero exits are surfaced
as exceptions. Nothing here ever interprets file contents as a command.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


class CommandRunner(Protocol):
    """Callable shape of :func:`run_command`, injectable into backends for tests."""

    def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
        input_text: str | None = None,
    ) -> CommandResult: ...


def run_command(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout: float,
    input_text: str | None = None,
) -> CommandResult:
    """Run ``argv`` with no shell, capturing output.

    Raises ``ValueError`` for empty argv or arguments containing NUL bytes,
    ``subprocess.TimeoutExpired`` on timeout, and ``subprocess.CalledProcessError``
    on a nonzero exit.
    """
    args = list(argv)
    if not args:
        raise ValueError("argv must be a non-empty command list")
    for arg in args:
        if "\x00" in arg:
            raise ValueError("argv arguments must not contain NUL bytes")

    completed = subprocess.run(
        args,
        cwd=str(cwd),
        timeout=timeout,
        input=input_text,
        capture_output=True,
        text=True,
        shell=False,
        check=True,
    )
    return CommandResult(
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )
