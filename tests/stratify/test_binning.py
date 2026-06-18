"""Binning: deterministic fixed + quantile bins with documented tie handling."""

from __future__ import annotations

import pytest

from veritas.stratify import fixed_bins, quantile_bins


def test_fixed_bins_edges_are_deterministic_and_even() -> None:
    bins = fixed_bins(4, lo=0.0, hi=1.0)
    assert bins.edges == (0.0, 0.25, 0.5, 0.75, 1.0)
    assert fixed_bins(4, lo=0.0, hi=1.0).edges == bins.edges  # stable across calls


def test_fixed_bins_assign_is_half_open_lower_inclusive() -> None:
    bins = fixed_bins(4, lo=0.0, hi=1.0)
    # value on an internal edge goes to the UPPER bucket (deterministic tie rule)
    assert bins.assign(0.0) == 0
    assert bins.assign(0.24) == 0
    assert bins.assign(0.25) == 1
    assert bins.assign(0.50) == 2
    assert bins.assign(0.75) == 3


def test_fixed_bins_top_edge_is_inclusive_in_last_bucket() -> None:
    bins = fixed_bins(4, lo=0.0, hi=1.0)
    assert bins.assign(1.0) == 3  # hi is inclusive for the final bin (not a 5th bucket)


def test_fixed_bins_clamp_out_of_range_values() -> None:
    bins = fixed_bins(4, lo=0.0, hi=1.0)
    assert bins.assign(-5.0) == 0
    assert bins.assign(9.0) == 3


def test_quantile_bins_split_on_value_distribution() -> None:
    # Median split of 0..9 -> edge at 4.5; deterministic.
    bins = quantile_bins([float(v) for v in range(10)], 2)
    assert bins.n_bins() == 2
    assert bins.assign(0.0) == 0
    assert bins.assign(9.0) == 1
    assert quantile_bins([float(v) for v in range(10)], 2).edges == bins.edges


def test_invalid_bin_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        fixed_bins(0)
    with pytest.raises(ValueError):
        quantile_bins([1.0, 2.0], 0)


def test_fixed_bins_requires_hi_above_lo() -> None:
    with pytest.raises(ValueError):
        fixed_bins(4, lo=1.0, hi=1.0)


def test_quantile_bins_requires_values() -> None:
    with pytest.raises(ValueError):
        quantile_bins([], 2)
