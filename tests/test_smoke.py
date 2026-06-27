"""Phase 0 smoke test: the package imports and exposes a version.

Authored test-first (docs/SPEC.md first principle #2): this fails until the
``veritas`` package exists with a ``__version__`` attribute.
"""

from __future__ import annotations

import veritas


def test_version_is_non_empty_string() -> None:
    assert isinstance(veritas.__version__, str)
    assert veritas.__version__ != ""
