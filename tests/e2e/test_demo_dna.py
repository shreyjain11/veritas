"""(d) Demo 3/3 -- regulatory DNA task, NUCLEOTIDE sequence detector.

Classification: NOT hermetic. Needs the regulatory-DNA dataset (external/opt-in)
and the pinned mmseqs2 binary (binary-backed). Exercises the sequence detector on
the nucleotide alphabet (the family/structural detectors are protein-only). Opt-in.
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


def test_regulatory_dna_nucleotide_leakage() -> None:
    root = Path(demo_data_or_skip("regulatory_dna"))
    benchmark = load_benchmark(
        root / "eval.fasta",
        root / "labels.csv",
        seq_type=SeqType.NUCLEOTIDE,
        metric=MetricSpec(name=MetricName.AUROC),
        split=SplitSpec(name="chrom-holdout", kind="chromosome"),
    )
    reference = load_reference_set(root / "reference.fasta", seq_type=SeqType.NUCLEOTIDE)
    config = AuditConfig(
        detectors=(
            DetectorConfig(kind=DetectorKind.SEQUENCE, name="mmseqs", identity_threshold=0.8),
        ),
        seed=1729,
        stratify_axes=("identity_to_nearest_reference",),
    )
    report = run_audit(config, AuditInputs(benchmark=benchmark, reference_items=reference))
    assert report.status is ResultStatus.OK
    assert report.leakage.n_eval > 0
