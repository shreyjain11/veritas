"""Scale: a 10k-eval x 10k-reference audit within a committed time ceiling (PLAN §8).

Marked `scale` (+ `slow`, binary-backed): excluded from the core run
(`-m "not external and not scale"`) and run on the CI runner's scale step. Not part
of the (a)-(e) review set -- included for PLAN completeness.
"""

from __future__ import annotations

import time

import pytest

from veritas.audit import run_audit
from veritas.contracts import (
    AuditConfig,
    AuditInputs,
    Benchmark,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    MetricName,
    MetricSpec,
    ReferenceItem,
    SeqType,
    SplitSpec,
)

pytestmark = [pytest.mark.scale, pytest.mark.slow, pytest.mark.requires_mmseqs]

_N = 10_000
_CEILING_SECONDS = 900.0  # committed ceiling on the CI runner; tunable


def _synthetic_sequence(seed: int) -> str:
    alphabet = "ACDEFGHIKLMNPQRSTVWY"
    return "".join(alphabet[(seed * 7 + i * 13) % 20] for i in range(40))


def test_audit_10k_within_time_ceiling() -> None:
    eval_items = tuple(
        EvalItem(
            id=f"e{i}",
            seq_type=SeqType.PROTEIN,
            sequence=_synthetic_sequence(i),
            label=float(i % 2),
            prediction=float((i % 2) ^ (i % 3 == 0)),
        )
        for i in range(_N)
    )
    reference_items = tuple(
        ReferenceItem(id=f"r{i}", seq_type=SeqType.PROTEIN, sequence=_synthetic_sequence(i))
        for i in range(_N)
    )
    benchmark = Benchmark(
        name="scale10k",
        eval_items=eval_items,
        split=SplitSpec(name="scale", kind="holdout"),
        metric=MetricSpec(name=MetricName.AUROC),
    )
    config = AuditConfig(
        detectors=(
            DetectorConfig(kind=DetectorKind.SEQUENCE, name="mmseqs", identity_threshold=0.5),
        ),
        seed=1729,
        bootstrap_n=200,
    )
    start = time.perf_counter()
    report = run_audit(config, AuditInputs(benchmark=benchmark, reference_items=reference_items))
    assert time.perf_counter() - start < _CEILING_SECONDS
    assert report.leakage.n_eval == _N
