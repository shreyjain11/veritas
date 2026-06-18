"""Differential tests for the hand-rolled metrics vs scikit-learn (test-only, req #3).

scikit-learn is an independent reference for our numpy implementations of AUROC,
AUPRC, accuracy, MCC, and F1. (Spearman/Pearson use scipy at runtime, so they are
covered by the golden tests rather than a circular scipy-vs-scipy differential.)
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st
from sklearn import metrics as skm

from veritas.contracts import MetricName
from veritas.metrics import compute_metric

_TOL = 1e-9


@st.composite
def _binary_dataset(draw: st.DrawFn) -> tuple[np.ndarray, np.ndarray]:
    size = draw(st.integers(min_value=4, max_value=40))
    labels = draw(st.lists(st.sampled_from([0.0, 1.0]), min_size=size, max_size=size))
    assume(0.0 in labels and 1.0 in labels)  # both classes present
    scores = draw(
        st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=size,
            max_size=size,
        )
    )
    return np.array(labels, dtype=float), np.array(scores, dtype=float)


@example((np.array([0.0, 1.0, 0.0, 1.0]), np.array([0.3, 0.3, 0.3, 0.3])))  # pin: all-equal scores
@given(_binary_dataset())
def test_auroc_matches_sklearn(data: tuple[np.ndarray, np.ndarray]) -> None:
    labels, scores = data
    assert compute_metric(MetricName.AUROC, labels, scores) == pytest.approx(
        float(skm.roc_auc_score(labels, scores)), abs=_TOL
    )


@given(_binary_dataset())
def test_auprc_matches_sklearn(data: tuple[np.ndarray, np.ndarray]) -> None:
    labels, scores = data
    assert compute_metric(MetricName.AUPRC, labels, scores) == pytest.approx(
        float(skm.average_precision_score(labels, scores)), abs=_TOL
    )


@example(
    (np.array([0.0, 1.0, 0.0, 1.0]), np.array([0.5, 0.5, 0.5, 0.5]))
)  # pin: all-equal at 0.5 threshold
@given(_binary_dataset())
def test_accuracy_matches_sklearn(data: tuple[np.ndarray, np.ndarray]) -> None:
    labels, scores = data
    predicted = (scores >= 0.5).astype(float)
    assert compute_metric(MetricName.ACCURACY, labels, scores, threshold=0.5) == pytest.approx(
        float(skm.accuracy_score(labels, predicted)), abs=_TOL
    )


@given(_binary_dataset())
def test_mcc_matches_sklearn(data: tuple[np.ndarray, np.ndarray]) -> None:
    labels, scores = data
    predicted = (scores >= 0.5).astype(float)
    assert compute_metric(MetricName.MCC, labels, scores, threshold=0.5) == pytest.approx(
        float(skm.matthews_corrcoef(labels, predicted)), abs=_TOL
    )


@given(_binary_dataset())
def test_f1_matches_sklearn(data: tuple[np.ndarray, np.ndarray]) -> None:
    labels, scores = data
    predicted = (scores >= 0.5).astype(float)
    assert compute_metric(MetricName.F1, labels, scores, threshold=0.5) == pytest.approx(
        float(skm.f1_score(labels, predicted, zero_division=0.0)), abs=_TOL
    )
