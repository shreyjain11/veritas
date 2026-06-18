"""Runtime capture of backend tool versions (docs/PLAN.md req C).

The runner is injectable so tests stay hermetic; the default runner shells out
to the tool and is exercised for real against the pinned binaries in Phase 2.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence

#: A runner takes an argv list and returns the tool's version output.
Runner = Callable[[Sequence[str]], str]

_UNAVAILABLE = "unavailable"


def _default_runner(args: Sequence[str]) -> str:
    result = subprocess.run(list(args), capture_output=True, text=True, check=True)
    return (result.stdout or result.stderr).strip()


def capture_tool_versions(
    tools: Sequence[str], *, runner: Runner = _default_runner
) -> dict[str, str]:
    """Return ``{tool: version_string}``; a tool that cannot be queried maps to "unavailable"."""
    versions: dict[str, str] = {}
    for tool in tools:
        try:
            versions[tool] = runner([tool, "version"])
        except (OSError, subprocess.SubprocessError):
            versions[tool] = _UNAVAILABLE
    return versions
