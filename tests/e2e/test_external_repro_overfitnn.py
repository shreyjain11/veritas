"""(e) External reproduction R3 -- the OverfitNN METRIC reproduction (the centerpiece).

We do NOT reproduce hashFrag's headline number. Instead we CONSTRUCT the maximally-overfit
memorizer hashFrag describes -- predict each test sequence's activity from the label of its
most sequence-similar training sequence -- and show Veritas recovers the inflation that
memorizer's reliance on homology predicts.

  hashFrag (bioRxiv 2025.01.22.634321, v2): genome-trained models "rely on memorized
  associations, inflating performance when function is conserved between homologs" -- a
  maximally overfit model with no understanding of regulation can score on test sequences
  similar to its training data. OverfitNN is exactly that model, made explicit.

OverfitNN is a DELIBERATELY TERRIBLE memorizer; the point is not that it looks good, but
that Veritas attributes its apparent signal to leakage.

Two splits are locked, with split-specific assertions tied to the observed (deterministic,
seed=1729, 20k train / 5k test) numbers:

  random split  -- the textbook signature: large inflation AND honest metric collapses to a
                   statistical null (honest CI includes 0). "Complete" leakage.
  chr8+chr9     -- the conservative, realistic case: even leakage-AWARE chromosome splitting
                   leaves residual moderate-homology that still inflates ~60% of the apparent
                   signal. Honest is REDUCED but NOT null (its CI excludes 0) -- that is the
                   finding, so we do not assert honest-is-null here.

Determinism note: the data prep sorts by id before the seeded subsample. Without that,
polars.unique() does not preserve row order, so the subsample (hence the numbers) varied
run to run -- a reproducibility bug found while locking this test and fixed here.

Dataset: Gosai et al. 2024 human lentiMPRA (de Boer lab), FETCH-ONLY (see
demos/regulatory_dna_gosai/manifest.toml; CC-BY-4.0 on the GAME Zenodo record, never
vendored here). Opt-in (external + binary-backed); runs when VERITAS_DEMO_DATA points at
the fetched, checksum-verified Gosai archive.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import polars as pl
import pytest

from tests.e2e import demo_data_or_skip
from veritas.audit import run_audit
from veritas.contamination.backends.mmseqs import MmseqsSearch
from veritas.contracts import (
    AuditConfig,
    AuditInputs,
    AuditReport,
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
from veritas.demos.overfitnn import overfitnn_predictions

pytestmark = [pytest.mark.external, pytest.mark.requires_mmseqs]

_GOSAI_TXT = "41586_2024_8070_MOESM4_ESM.txt"
_GOSAI_ZIP_MEMBER = f"evaluator_data/{_GOSAI_TXT}"
_GOSAI_ARCHIVE_SHA256 = "dcdd92c42cb12cfcf9c2d60cb3e522811dfad437078693811aa0674d0da9d3e1"

_SEED, _N_TRAIN, _N_TEST = 1729, 20000, 5000
_IDENTITY_THRESHOLD = 0.80  # nucleotide identity at/above which a test item is train-homologous
_TEST_CHROMOSOMES = ("8", "9")

# Inflation floors are REGRESSION GUARDS, never published-magnitude claims. The real
# significance bound in every case is "delta CI excludes 0".
#   random split:  observed delta 0.147 (CI [0.107, 0.186]) -> 0.04 floor cleared with margin.
#   chr8+chr9:     observed delta 0.0445 (CI [0.009, 0.079]) -> deliberately LOOSE 0.02 floor,
#                  NOT tuned to the CI edge; the CI-excludes-0 (low 0.009) is the real bound.
_RANDOM_MIN_INFLATION = 0.04
_CHR_HOLDOUT_MIN_INFLATION = 0.02


def _gosai_dataframe(root: Path) -> pl.DataFrame:
    txt = root / _GOSAI_TXT
    if not txt.exists():
        archive = root / "evaluator_data.zip"
        if not archive.exists():
            pytest.skip(f"Gosai data not found under {root} (expected {txt} or {archive})")
        with zipfile.ZipFile(archive) as zf:
            txt.write_bytes(zf.read(_GOSAI_ZIP_MEMBER))
    frame = pl.read_csv(
        txt,
        separator="\t",
        columns=["IDs", "chr", "K562_log2FC", "sequence"],
        schema_overrides={"IDs": pl.String, "chr": pl.String, "sequence": pl.String},
        infer_schema_length=20000,
    )
    return (
        frame.with_columns(
            pl.col("K562_log2FC").cast(pl.Float64, strict=False),
            pl.col("chr").str.replace(r"^chr", "").alias("chrn"),
        )
        .drop_nulls(["IDs", "sequence", "K562_log2FC", "chrn"])
        .filter(pl.col("sequence").str.to_uppercase().str.contains(r"^[ACGTUNRYSWKMBDHV]+$"))
        .unique(subset=["IDs"], keep="first")
        .sort("IDs")  # deterministic total order so the seeded subsample is reproducible
    )


def _references(frame: pl.DataFrame) -> tuple[tuple[ReferenceItem, ...], dict[str, float]]:
    refs = tuple(
        ReferenceItem(id=r["IDs"], seq_type=SeqType.NUCLEOTIDE, sequence=r["sequence"])
        for r in frame.iter_rows(named=True)
    )
    labels = {r["IDs"]: float(r["K562_log2FC"]) for r in frame.iter_rows(named=True)}
    return refs, labels


def _evals(frame: pl.DataFrame) -> tuple[EvalItem, ...]:
    return tuple(
        EvalItem(
            id=r["IDs"],
            seq_type=SeqType.NUCLEOTIDE,
            sequence=r["sequence"],
            label=float(r["K562_log2FC"]),
        )
        for r in frame.iter_rows(named=True)
    )


def _audit(train_df: pl.DataFrame, test_df: pl.DataFrame, split_name: str) -> AuditReport:
    references, reference_labels = _references(train_df)
    test_items = _evals(test_df)
    # The memorizer hashFrag describes (deterministic; same mmseqs path the detector uses).
    predictions = overfitnn_predictions(test_items, references, reference_labels, MmseqsSearch())
    benchmark = Benchmark(
        name=f"gosai_k562_overfitnn_{split_name}",
        eval_items=tuple(
            item.model_copy(update={"prediction": predictions[item.id]}) for item in test_items
        ),
        split=SplitSpec(name=split_name, kind="genomic"),
        metric=MetricSpec(name=MetricName.SPEARMAN),
    )
    config = AuditConfig(
        detectors=(
            DetectorConfig(
                kind=DetectorKind.SEQUENCE, name="mmseqs", identity_threshold=_IDENTITY_THRESHOLD
            ),
        ),
        seed=_SEED,
        stratify_axes=("identity_to_nearest_reference",),
    )
    return run_audit(
        config,
        AuditInputs(benchmark=benchmark, reference_items=references),
        dataset_hashes={"dataset:regulatory_dna_gosai:evaluator_data.zip": _GOSAI_ARCHIVE_SHA256},
    )


def test_overfitnn_random_split_complete_memorizer_collapse() -> None:
    # Observed (seed 1729, 20k/5k): reported 0.165, honest 0.018 [-0.016, 0.050],
    # delta 0.147 [0.107, 0.186], leakage 1230/5000 = 24.6%.
    df = _gosai_dataframe(Path(demo_data_or_skip("regulatory_dna_gosai")))
    shuffled = df.sample(fraction=1.0, shuffle=True, seed=_SEED)
    report = _audit(shuffled.slice(_N_TEST, _N_TRAIN), shuffled.head(_N_TEST), "random_split")

    assert report.reported is not None and report.honest is not None and report.delta is not None
    reported, honest, delta = report.reported, report.honest, report.delta
    assert reported.status.value == "ok" and honest.status.value == "ok"  # status ok
    assert delta.value is not None and delta.value > 0.0  # sign: inflation
    assert delta.value >= _RANDOM_MIN_INFLATION  # magnitude (regression guard; observed 0.147)
    assert delta.ci_low is not None and delta.ci_low > 0.0  # significant: delta CI excludes 0
    # memorizer signature: de-leaked honest metric collapses to a statistical null.
    assert honest.ci_low is not None and honest.ci_high is not None
    assert honest.ci_low <= 0.0 <= honest.ci_high  # observed [-0.016, 0.050]


def test_overfitnn_chr_holdout_partial_residual_leakage() -> None:
    # Observed (seed 1729, 20k/5k): reported 0.074, honest 0.0295 [0.0021, 0.0556],
    # delta 0.0445 [0.009, 0.079], leakage 828/5000 = 16.6%. Even a leakage-AWARE chromosome
    # split leaves residual moderate-homology: honest is REDUCED but its CI excludes 0, so we
    # do NOT assert honest-is-null here -- that is the finding.
    df = _gosai_dataframe(Path(demo_data_or_skip("regulatory_dna_gosai")))
    test_pool = df.filter(pl.col("chrn").is_in(list(_TEST_CHROMOSOMES)))
    train_pool = df.filter(~pl.col("chrn").is_in(list(_TEST_CHROMOSOMES)))
    report = _audit(
        train_pool.sample(n=min(_N_TRAIN, train_pool.height), seed=_SEED),
        test_pool.sample(n=min(_N_TEST, test_pool.height), seed=_SEED),
        "chr8_9_holdout",
    )

    assert report.reported is not None and report.honest is not None and report.delta is not None
    reported, honest, delta = report.reported, report.honest, report.delta
    assert reported.status.value == "ok" and honest.status.value == "ok"  # status ok
    assert delta.value is not None and delta.value > 0.0  # sign: inflation
    assert delta.value >= _CHR_HOLDOUT_MIN_INFLATION  # loose regression guard (observed 0.0445)
    assert (
        delta.ci_low is not None and delta.ci_low > 0.0
    )  # the rigorous bound (observed low 0.009)
    # substantial-but-NOT-complete reduction: honest is well below reported (~60% is leakage).
    assert reported.value is not None and honest.value is not None
    assert honest.value <= 0.6 * reported.value  # observed 0.0295 <= 0.6 * 0.074 = 0.0444


# --- real-row adapter assertion (requirement #1) ------------------------------------------
# Hand-verified from the actual Gosai file (columns IDs, chr, ..., K562_log2FC, ..., sequence),
# read verbatim from the real download:
_GOSAI_REAL_ROWS = (
    {
        "id": "7:70038969:G:T:A:wC",
        "chr": "7",
        "k562_log2fc": 0.0607792388454394,
        "seq_prefix": "CCTGGTCTTTCTTGCTAAAT",
    },
    {
        "id": "1:192696196:C:T:A:wC",
        "chr": "1",
        "k562_log2fc": 0.3796391272646789,
        "seq_prefix": "CATAAAGATGAGGCTTGGCAAAG",
    },
)


def test_regulatory_dna_adapter_maps_real_gosai_rows(tmp_path: Path) -> None:
    root = Path(demo_data_or_skip("regulatory_dna_gosai"))
    wanted = [str(row["id"]) for row in _GOSAI_REAL_ROWS]
    df = _gosai_dataframe(root).filter(pl.col("IDs").is_in(wanted))
    assert df.height == len(_GOSAI_REAL_ROWS)  # both hand-verified rows present in the real file
    normalized = df.select(
        pl.col("IDs").alias("id"),
        pl.col("sequence"),
        pl.col("K562_log2FC").alias("label"),
        pl.lit(0.0).alias("prediction"),  # placeholder; the mapping under test is id/seq/label/chr
        pl.col("chrn").alias("chromosome"),
    )
    eval_csv = tmp_path / "gosai_eval.csv"
    normalized.write_csv(eval_csv)
    ref_csv = tmp_path / "gosai_ref.csv"
    ref_csv.write_text("id,sequence\nr1,ACGTACGT\n", encoding="utf-8")

    from veritas.demos.regulatory_dna import RegulatoryDNAAdapter

    items = RegulatoryDNAAdapter(eval_table=eval_csv, reference_table=ref_csv).load_benchmark()
    by_id = {item.id: item for item in items.eval_items}
    for expected in _GOSAI_REAL_ROWS:
        item = by_id[str(expected["id"])]
        assert item.seq_type is SeqType.NUCLEOTIDE
        assert item.sequence.startswith(str(expected["seq_prefix"]))
        assert item.label == pytest.approx(expected["k562_log2fc"])
        assert item.metadata["chromosome"] == expected["chr"]
