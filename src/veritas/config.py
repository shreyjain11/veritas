"""Runtime path/configuration resolution for Veritas.

Plumbing only — no domain logic lives here. The cache directory holds expensive
detector-search results (Phase 2+); this module just decides *where* that is,
honouring an explicit override, then the XDG base-directory spec, then a home
fallback (docs/PLAN.md decision #17).
"""

from __future__ import annotations

import os
from pathlib import Path

#: Environment variable that, when set, overrides the cache directory verbatim.
CACHE_DIR_ENV = "VERITAS_CACHE_DIR"
#: XDG base-directory variable consulted when the override is unset.
XDG_CACHE_HOME_ENV = "XDG_CACHE_HOME"
#: Cache subdirectory name placed under the resolved base directory.
CACHE_SUBDIR = "veritas"


def cache_dir() -> Path:
    """Return the Veritas cache directory (does not create it).

    Resolution order:

    1. ``$VERITAS_CACHE_DIR`` if set, used verbatim (``~`` expanded).
    2. ``$XDG_CACHE_HOME/veritas`` if ``XDG_CACHE_HOME`` is set.
    3. ``~/.cache/veritas`` otherwise.
    """
    override = os.environ.get(CACHE_DIR_ENV)
    if override:
        return Path(override).expanduser()

    xdg = os.environ.get(XDG_CACHE_HOME_ENV)
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base.expanduser() / CACHE_SUBDIR
