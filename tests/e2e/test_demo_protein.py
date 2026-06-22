"""(d) Demo -- ProteinGym MSA-depth stratification of ESM-1v (no contamination claim).

CLAIM (correlational, NOT causal): Veritas's stratification axis recovers the known MSA-depth
performance gradient ESM-1v and ProteinGym document -- ESM-1v's MEAN per-assay Spearman rises
with MSA depth (Low 0.298 < Medium 0.384 < High 0.531).

Caveats (prominent, verbatim):
- correlational, not causal;
- residual confounds: MSA depth correlates with protein family / organism / assay-type, and
  observational data cannot fully de-confound the depth effect from those;
- WIDE within-bucket spread with OVERLAPPING ranges -- a shift in the mean, not clean
  separation (e.g. GFP 0.047 sits in Low, CALM1 0.264 in High).

Method (the correct granularity for cross-assay-scale data): per-assay Spearman, then per
bucket the MEAN of per-assay Spearman. This deliberately does NOT use Veritas's item-pooling
``categorical_performance_curve`` -- pooling variants across assays of different DMS scales
would be invalid. Selection is neutral: per ProteinGym ``MSA_Neff_L_category``, single_mutants
>= 100, present in the scores zip, alphabetical by DMS_id, first 15. Baseline = ESM-1v ensemble
(Meier et al., NeurIPS 2021). Fetch-only (demos/proteingym_dms/manifest.toml); opt-in.
"""

from __future__ import annotations

import io
import statistics
import zipfile
from pathlib import Path

import polars as pl
import pytest

from tests.e2e import demo_data_or_skip
from veritas.contracts import MetricName
from veritas.metrics import compute_metric

pytestmark = [pytest.mark.external]

_BASELINE = "ESM1v_ensemble"
_N_PER_BUCKET = 15
_MIN_SINGLE_MUTANTS = 100
_MIN_VALID = 30
# High - Low must clear this margin: the test fails if the gradient FLATTENS, not only if it
# inverts. Observed High 0.531 - Low 0.298 = 0.233.
_MIN_GRADIENT = 0.15


def _mean_per_assay_spearman(root: Path, category: str) -> float:
    ref = pl.read_csv(root / "DMS_substitutions.csv", infer_schema_length=20000)
    archive = zipfile.ZipFile(root / "zero_shot_substitutions_scores.zip")
    present = {name for name in archive.namelist() if name.endswith(".csv")}
    candidates = (
        ref.filter(
            (pl.col("MSA_Neff_L_category") == category)
            & (pl.col("DMS_number_single_mutants") >= _MIN_SINGLE_MUTANTS)
        )
        .sort("DMS_id")["DMS_id"]
        .to_list()
    )
    spearmans: list[float] = []
    for dms in candidates:
        name = f"{dms}.csv"
        if name not in present:
            continue
        df = pl.read_csv(io.BytesIO(archive.read(name)), columns=["mutant", "DMS_score", _BASELINE])
        df = df.filter(~pl.col("mutant").str.contains(":")).drop_nulls(["DMS_score", _BASELINE])
        if df.height < _MIN_VALID:
            continue
        labels = df["DMS_score"].to_numpy().astype(float)
        preds = df[_BASELINE].to_numpy().astype(float)
        spearmans.append(compute_metric(MetricName.SPEARMAN, labels, preds, threshold=0.5))
        if len(spearmans) >= _N_PER_BUCKET:
            break
    assert len(spearmans) == _N_PER_BUCKET, f"{category}: found only {len(spearmans)} assays"
    return statistics.mean(spearmans)


def test_proteingym_msa_depth_gradient() -> None:
    root = Path(demo_data_or_skip("proteingym_dms"))
    low = _mean_per_assay_spearman(root, "Low")
    medium = _mean_per_assay_spearman(root, "Medium")
    high = _mean_per_assay_spearman(root, "High")
    # Monotonic mean ordering with a margin (numbers recorded in docs/validation.md).
    assert low < medium < high
    assert high - low > _MIN_GRADIENT
