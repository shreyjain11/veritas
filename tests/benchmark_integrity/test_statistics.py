from __future__ import annotations

import pytest

from veritas.benchmark_integrity.statistics import (
    benjamini_hochberg,
    mcnemar_exact,
    paired_bootstrap_gap,
    paired_permutation_p_value,
)


def test_paired_statistics_are_deterministic_and_parent_paired() -> None:
    canonical = [1.0, 1.0, 1.0, 0.0]
    transformed = [0.0, 0.0, 1.0, 0.0]
    assert paired_bootstrap_gap(canonical, transformed, seed=7) == paired_bootstrap_gap(
        canonical, transformed, seed=7
    )
    assert 0.0 < paired_permutation_p_value(canonical, transformed, seed=7) <= 1.0
    result = mcnemar_exact([True, True, True, False], [False, False, True, False])
    assert result["canonical_only"] == 2
    assert result["transformed_only"] == 0


def test_benjamini_hochberg_preserves_input_order() -> None:
    adjusted = benjamini_hochberg([0.04, 0.001, 0.02])
    assert adjusted == pytest.approx((0.04, 0.003, 0.03))


def test_paired_statistics_reject_unpaired_inputs() -> None:
    with pytest.raises(ValueError, match="equal"):
        paired_bootstrap_gap([1.0], [])
