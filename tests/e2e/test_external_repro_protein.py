"""(e) External reproduction 1/2 -- published protein-interaction homology leakage.

Provisional target (#12): arXiv 2404.10457, a known PPI-benchmark homology-leakage
result. Veritas must recover the reported honest-vs-reported gap within a stated
tolerance. Marked external (+ binary-backed); the dataset and the exact tolerance
are fixed when the data lands, so the body skips until then. Opt-in job only.
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

# Published delta (reported - honest) and tolerance; pinned once the dataset is fixed (#12).
_PUBLISHED_DELTA = 0.0
_TOLERANCE = 0.0


def test_reproduces_published_ppi_homology_leakage() -> None:
    root = Path(demo_data_or_skip("repro_protein_2404.10457"))
    if _TOLERANCE == 0.0:
        pytest.skip("external-repro tolerance pending dataset fix (#12)")
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
            DetectorConfig(kind=DetectorKind.SEQUENCE, name="mmseqs", identity_threshold=0.3),
        ),
        seed=1729,
    )
    report = run_audit(config, AuditInputs(benchmark=benchmark, reference_items=reference))
    assert report.delta.value is not None
    assert abs(report.delta.value - _PUBLISHED_DELTA) <= _TOLERANCE
