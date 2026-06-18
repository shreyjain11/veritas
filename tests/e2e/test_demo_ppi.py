"""(d) Demo 2/3 -- protein function/interaction, FAMILY + STRUCTURAL detectors.

Classification: NOT hermetic. Needs the benchmark dataset (external/opt-in), the
full Pfam-A database (requires_pfam, network), and the pinned foldseek binary
(binary-backed). Exercises the family (pyhmmer+Pfam) and structural (foldseek)
detectors composed by union. Opt-in job only.
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

pytestmark = [
    pytest.mark.external,
    pytest.mark.requires_foldseek,
    pytest.mark.requires_hmmer,
    pytest.mark.requires_pfam,
]


def test_ppi_family_and_structural_leakage() -> None:
    root = Path(demo_data_or_skip("ppi"))
    benchmark = load_benchmark(
        root / "eval.fasta",
        root / "labels.csv",
        seq_type=SeqType.PROTEIN,
        metric=MetricSpec(name=MetricName.AUROC),
        split=SplitSpec(name="ppi", kind="holdout"),
    )
    reference = load_reference_set(root / "reference.fasta", seq_type=SeqType.PROTEIN)
    config = AuditConfig(
        detectors=(
            DetectorConfig(kind=DetectorKind.FAMILY, name="pyhmmer", e_value_threshold=1e-5),
            DetectorConfig(kind=DetectorKind.STRUCTURE, name="foldseek", score_threshold=0.5),
        ),
        seed=1729,
    )
    report = run_audit(config, AuditInputs(benchmark=benchmark, reference_items=reference))
    assert report.status is ResultStatus.OK
    assert report.leakage.per_detector  # both detectors contributed edges
