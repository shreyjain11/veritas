"""Resolve detector binaries to absolute paths once, up front.

Security (deferred hardening): backends used to invoke a bare tool name (``mmseqs``)
whose meaning depends on ``$PATH`` ordering at exec time -- a binary planted earlier
on PATH would silently run. Instead each backend resolves its tool to an absolute
path at construction (operator pin ``VERITAS_<TOOL>_BIN`` wins over PATH) and runs
that exact path thereafter; the resolved path is recorded in the provenance manifest.
"""

from __future__ import annotations

import shutil


def env_var_for(name: str) -> str:
    """The operator-pin env var for a tool, e.g. ``mmseqs`` -> ``VERITAS_MMSEQS_BIN``."""
    return "VERITAS_" + name.upper().replace("-", "_") + "_BIN"


def resolve_executable(name: str, *, environ: dict[str, str] | None = None) -> str | None:
    """Absolute path for ``name``: an operator pin (``VERITAS_<TOOL>_BIN``) else PATH.

    Returns ``None`` when the tool cannot be found, so construction stays non-fatal:
    a backend falls back to the bare name (and the subprocess fails clearly) only when
    no binary exists at all -- whenever one does exist, the absolute path is used.
    """
    import os

    env = os.environ if environ is None else environ
    override = env.get(env_var_for(name))
    if override:
        return override  # operator-pinned: trusted as given
    return shutil.which(name, path=env.get("PATH"))
