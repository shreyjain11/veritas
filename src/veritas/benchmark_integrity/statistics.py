"""Paired, parent-item statistics for benchmark transformations."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy.stats import binomtest


def paired_bootstrap_gap(
    canonical: Sequence[float],
    transformed: Sequence[float],
    *,
    samples: int = 2_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    left, right = _arrays(canonical, transformed)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, left.size, size=(samples, left.size))
    gaps = (left[indices] - right[indices]).mean(axis=1)
    alpha = (1 - confidence) / 2
    return float(np.quantile(gaps, alpha)), float(np.quantile(gaps, 1 - alpha))


def paired_permutation_p_value(
    canonical: Sequence[float],
    transformed: Sequence[float],
    *,
    samples: int = 5_000,
    seed: int = 42,
) -> float:
    left, right = _arrays(canonical, transformed)
    differences = left - right
    observed = abs(float(differences.mean()))
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(samples, differences.size))
    permuted = np.abs((signs * differences).mean(axis=1))
    return float((np.count_nonzero(permuted >= observed) + 1) / (samples + 1))


def mcnemar_exact(canonical: Sequence[bool], transformed: Sequence[bool]) -> dict[str, float | int]:
    left, right = _arrays(canonical, transformed)
    canonical_only = int(np.count_nonzero((left == 1) & (right == 0)))
    transformed_only = int(np.count_nonzero((left == 0) & (right == 1)))
    discordant = canonical_only + transformed_only
    p_value = (
        1.0
        if discordant == 0
        else float(binomtest(min(canonical_only, transformed_only), discordant, 0.5).pvalue)
    )
    return {
        "canonical_only": canonical_only,
        "transformed_only": transformed_only,
        "discordant": discordant,
        "p_value": p_value,
    }


def benjamini_hochberg(values: Sequence[float]) -> tuple[float, ...]:
    if not values:
        return ()
    indexed = sorted(enumerate(values), key=lambda pair: pair[1])
    adjusted = [0.0] * len(values)
    running = 1.0
    for reverse_rank, (index, value) in enumerate(reversed(indexed), start=1):
        rank = len(values) - reverse_rank + 1
        running = min(running, value * len(values) / rank)
        adjusted[index] = min(1.0, running)
    return tuple(adjusted)


def _arrays(
    canonical: Sequence[float] | Sequence[bool], transformed: Sequence[float] | Sequence[bool]
) -> tuple[np.ndarray, np.ndarray]:
    left = np.asarray(canonical, dtype=np.float64)
    right = np.asarray(transformed, dtype=np.float64)
    if left.ndim != 1 or left.size == 0 or left.shape != right.shape:
        raise ValueError("paired statistics require equal, non-empty one-dimensional samples")
    return left, right
