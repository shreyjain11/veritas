"""Runtime tool-version capture (req C): interface is injectable/mockable in Phase 1.

The default runner shells out to the pinned binaries (exercised for real in
Phase 2); here we inject a fake runner to keep the test hermetic/offline.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from veritas.provenance import capture_tool_versions
from veritas.provenance.tool_versions import _default_runner


def _fake_runner(args: Sequence[str]) -> str:
    tool = args[0]
    return {
        "mmseqs": "mmseqs version 18.8cc5c",
        "foldseek": "foldseek 10.941cd33",
    }[tool]


def test_capture_tool_versions_uses_injected_runner() -> None:
    versions = capture_tool_versions(("mmseqs", "foldseek"), runner=_fake_runner)
    assert versions == {
        "mmseqs": "mmseqs version 18.8cc5c",
        "foldseek": "foldseek 10.941cd33",
    }


def test_capture_tool_versions_marks_missing_tool_unavailable() -> None:
    def boom(args: Sequence[str]) -> str:
        raise FileNotFoundError(args[0])

    assert capture_tool_versions(("mmseqs",), runner=boom) == {"mmseqs": "unavailable"}


def test_default_runner_executes_a_command() -> None:
    # Exercises the real subprocess runner hermetically (no bio binary / network).
    assert _default_runner([sys.executable, "-c", "print('1.2.3')"]) == "1.2.3"
