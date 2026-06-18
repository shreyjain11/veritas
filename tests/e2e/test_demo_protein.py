"""(d) Demo 1/3 -- protein variant-effect (ProteinGym DMS), SEQUENCE detector.

Classification: NOT hermetic. Needs the ProteinGym dataset (external/opt-in) AND
the pinned mmseqs2 binary (binary-backed). Excluded from core CI (`-m "not external
and not scale"`); runs only in the opt-in network job with binaries present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e import demo_data_or_skip
from veritas.audit import run_audit
from veritas.contracts import (
    AuditConfig,
    AuditInputs,
    DetectorConfig,
    DetectorKind,
    MetricName,
    MetricSpec,
    ResultStatus,
    SeqType,
    SplitSpec,
)
from veritas.io.loaders import load_benchmark, load_reference_set

pytestmark = [pytest.mark.external, pytest.mark.requires_mmseqs]


def test_proteingym_dms_sequence_leakage() -> None:
    root = Path(demo_data_or_skip("proteingym"))
    benchmark = load_benchmark(
        root / "eval.fasta",
        root / "labels.csv",
        seq_type=SeqType.PROTEIN,
        metric=MetricSpec(name=MetricName.SPEARMAN),
        split=SplitSpec(name="dms", kind="dms"),
    )
    reference = load_reference_set(root / "reference.fasta", seq_type=SeqType.PROTEIN)
    config = AuditConfig(
        detectors=(
            DetectorConfig(kind=DetectorKind.SEQUENCE, name="mmseqs", identity_threshold=0.3),
        ),
        seed=1729,
        stratify_axes=("identity_to_nearest_reference",),
    )
    report = run_audit(config, AuditInputs(benchmark=benchmark, reference_items=reference))
    assert report.status is ResultStatus.OK
    assert report.leakage.n_eval > 0
    assert report.stratification  # robustness curve produced
