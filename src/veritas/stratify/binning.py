"""Deterministic binning of a difficulty axis into ordered buckets.

Bins are half-open ``[edge[i], edge[i+1])`` with the top edge folded into the
last bucket, so every real value maps to exactly one in-range bucket. A value on
an internal edge goes to the upper bucket (``side="right"``), a fixed tie rule.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Bins:
    #: Ascending bin edges, length ``n_bins + 1``.
    edges: tuple[float, ...]

    def n_bins(self) -> int:
        return len(self.edges) - 1

    def assign(self, value: float) -> int:
        """Bucket index for ``value`` (lower-inclusive; clamped into range)."""
        internal = self.edges[1:-1]  # the n_bins-1 internal cut points
        return int(np.searchsorted(internal, value, side="right"))


def fixed_bins(n_bins: int, lo: float = 0.0, hi: float = 1.0) -> Bins:
    """``n_bins`` equal-width bins spanning ``[lo, hi]``."""
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")
    if hi <= lo:
        raise ValueError("hi must be greater than lo")
    edges = tuple(float(lo + (hi - lo) * i / n_bins) for i in range(n_bins + 1))
    return Bins(edges=edges)


def quantile_bins(values: Sequence[float], n_bins: int) -> Bins:
    """``n_bins`` bins whose edges are the empirical quantiles of ``values``."""
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")
    if len(values) == 0:
        raise ValueError("quantile_bins requires at least one value")
    arr = np.asarray(values, dtype=np.float64)
    quantiles = np.linspace(0.0, 1.0, n_bins + 1)
    edges = np.quantile(arr, quantiles)
    return Bins(edges=tuple(float(edge) for edge in edges))
