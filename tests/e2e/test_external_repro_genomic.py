"""(e) External reproduction 2/2 -- genomic cross-chromosome leakage (hashFrag).

Provisional target (#12): a hashFrag-style cross-chromosome leakage finding on a
genome-trained model. Veritas must recover it within a stated tolerance. Marked
external (+ binary-backed, nucleotide sequence detector); dataset and tolerance
fixed when the data lands, so the body skips until then. Opt-in job only.
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
    SeqType,
    SplitSpec,
)
from veritas.io.loaders import load_benchmark, load_reference_set

pytestmark = [pytest.mark.external, pytest.mark.requires_mmseqs]

_PUBLISHED_DELTA = 0.0
_TOLERANCE = 0.0


def test_reproduces_cross_chromosome_leakage() -> None:
    root = Path(demo_data_or_skip("repro_genomic_hashfrag"))
    if _TOLERANCE == 0.0:
        pytest.skip("external-repro tolerance pending dataset fix (#12)")
    benchmark = load_benchmark(
        root / "eval.fasta",
        root / "labels.csv",
        seq_type=SeqType.NUCLEOTIDE,
        metric=MetricSpec(name=MetricName.AUROC),
        split=SplitSpec(name="chrom", kind="chromosome"),
    )
    reference = load_reference_set(root / "reference.fasta", seq_type=SeqType.NUCLEOTIDE)
    config = AuditConfig(
        detectors=(
            DetectorConfig(kind=DetectorKind.SEQUENCE, name="mmseqs", identity_threshold=0.8),
        ),
        seed=1729,
    )
    report = run_audit(config, AuditInputs(benchmark=benchmark, reference_items=reference))
    assert report.delta.value is not None
    assert abs(report.delta.value - _PUBLISHED_DELTA) <= _TOLERANCE
