"""Hand-computed golden values for every metric (known-answer tests)."""

from __future__ import annotations

import numpy as np
import pytest

from veritas.contracts import MetricName
from veritas.metrics import compute_metric


def test_auroc_perfectly_separable_is_one() -> None:
    labels = np.array([0.0, 0.0, 1.0, 1.0])
    scores = np.array([0.1, 0.2, 0.3, 0.4])
    assert compute_metric(MetricName.AUROC, labels, scores) == pytest.approx(1.0)


def test_auroc_reversed_is_zero() -> None:
    labels = np.array([0.0, 0.0, 1.0, 1.0])
    scores = np.array([0.4, 0.3, 0.2, 0.1])
    assert compute_metric(MetricName.AUROC, labels, scores) == pytest.approx(0.0)


def test_auroc_interleaved_is_three_quarters() -> None:
    # positives at scores 0.2 and 0.4; of the 4 pos/neg pairs, 3 are correctly ordered.
    labels = np.array([0.0, 1.0, 0.0, 1.0])
    scores = np.array([0.1, 0.2, 0.3, 0.4])
    assert compute_metric(MetricName.AUROC, labels, scores) == pytest.approx(0.75)


def test_auroc_all_ties_is_one_half() -> None:
    labels = np.array([0.0, 1.0, 0.0, 1.0])
    scores = np.array([0.5, 0.5, 0.5, 0.5])
    assert compute_metric(MetricName.AUROC, labels, scores) == pytest.approx(0.5)


def test_auprc_perfect_is_one() -> None:
    labels = np.array([0.0, 1.0])
    scores = np.array([0.1, 0.9])
    assert compute_metric(MetricName.AUPRC, labels, scores) == pytest.approx(1.0)


def test_auprc_hand_computed() -> None:
    # ranking 0.9(1), 0.5(0), 0.1(1): AP = (1/2)*1 + (1/2)*(2/3) = 0.8333...
    labels = np.array([1.0, 0.0, 1.0])
    scores = np.array([0.9, 0.5, 0.1])
    assert compute_metric(MetricName.AUPRC, labels, scores) == pytest.approx(5 / 6)


def test_spearman_monotonic_is_one_and_reversed_is_minus_one() -> None:
    labels = np.array([1.0, 2.0, 3.0, 4.0])
    assert compute_metric(MetricName.SPEARMAN, labels, np.array([10.0, 20.0, 30.0, 40.0])) == (
        pytest.approx(1.0)
    )
    assert compute_metric(MetricName.SPEARMAN, labels, np.array([40.0, 30.0, 20.0, 10.0])) == (
        pytest.approx(-1.0)
    )


def test_pearson_linear_is_one() -> None:
    labels = np.array([1.0, 2.0, 3.0])
    scores = np.array([2.0, 4.0, 6.0])
    assert compute_metric(MetricName.PEARSON, labels, scores) == pytest.approx(1.0)


def test_accuracy_thresholded() -> None:
    labels = np.array([0.0, 1.0, 1.0, 0.0])
    scores = np.array([0.2, 0.8, 0.9, 0.6])  # binarize@0.5 -> [0,1,1,1]; one wrong
    assert compute_metric(MetricName.ACCURACY, labels, scores, threshold=0.5) == pytest.approx(0.75)


def test_mcc_perfect_and_reversed() -> None:
    labels = np.array([0.0, 1.0, 0.0, 1.0])
    assert compute_metric(MetricName.MCC, labels, np.array([0.1, 0.9, 0.2, 0.8])) == (
        pytest.approx(1.0)
    )
    assert compute_metric(MetricName.MCC, labels, np.array([0.9, 0.1, 0.8, 0.2])) == (
        pytest.approx(-1.0)
    )


def test_f1_perfect_is_one() -> None:
    labels = np.array([0.0, 1.0, 1.0])
    scores = np.array([0.1, 0.9, 0.8])
    assert compute_metric(MetricName.F1, labels, scores, threshold=0.5) == pytest.approx(1.0)
