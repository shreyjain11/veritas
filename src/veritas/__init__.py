"""Veritas: a model-agnostic, post-hoc leakage & robustness auditor for
sequence-based biological predictors.

This top-level package is the importable core. Per SPEC §3 it must import
cleanly without the optional ``cli`` or ``mcp`` layers (and without the
test-only ``scikit-learn`` dependency) being present.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
