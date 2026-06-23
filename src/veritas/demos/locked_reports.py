"""The five locked demo results, serialized into AuditReport fixtures for the viewer.

This is SERIALIZATION of already-validated results, not new science: every number here
is a locked, e2e-validated, documented result. The science that produced each is proven
on real data by the cited test; this module records those results in the wire format.

Sources of truth (numbers must equal these bit-for-bit; tests/report/test_demo_fixtures.py
guards it):
  - R3 random / chr8+chr9  -> tests/e2e/test_external_repro_overfitnn.py + docs/validation.md
  - ProteinGym MSA-depth   -> tests/e2e/test_demo_protein.py + docs/validation.md
  - R2 reverse-complement  -> tests/e2e/test_external_repro_genomic.py + docs/validation.md
  - PPI splits-matrix      -> tests/e2e/test_demo_ppi.py + docs/validation.md

Dataset input-hashes are the pinned digests from each demo's demos/*/manifest.toml.
"""

from __future__ import annotations

from veritas.contracts import (
    AuditReport,
    DetectorCell,
    LeakageSplit,
    LeakageSummary,
    Limitation,
    MetricName,
    ProvenanceRecord,
    SplitRole,
    StratumResult,
    TracedValue,
)
from veritas.report import (
    assemble_detection_report,
    assemble_report,
    assemble_stratification_report,
)

_SEED = 1729
_FOLD_LEVEL_CAVEAT = Limitation(
    id="structural_fold_level",
    title="Structural detection is fold-level, not interface-level",
    detail=(
        "Veritas's structural detector reports a fold-level TM-score (foldseek monomer "
        "TMalign, max(qtmscore, ttmscore)) -- a related but more permissive signal than "
        "iDist's interface-level redundancy. The structural rates are reported as their own "
        "quantity and are not directly comparable to interface-redundancy baselines."
    ),
)


def _metric(name: str, value: float, lo: float, hi: float, ref: str) -> TracedValue:
    return TracedValue(name=name, value=value, provenance_ref=ref, ci_low=lo, ci_high=hi)


def _stratum(
    axis: str, idx: int, label: str, value: float, n: int, *, silent: bool
) -> StratumResult:
    return StratumResult(
        axis_name=axis,
        bucket_index=idx,
        bucket_label=label,
        n=n,
        metric=TracedValue(
            name=MetricName.SPEARMAN.value, value=value, provenance_ref=f"prov:{label}"
        ),
        is_silent_failure=silent,
    )


# Pinned dataset digests (from each demos/*/manifest.toml).
_GOSAI_HASH = "dcdd92c42cb12cfcf9c2d60cb3e522811dfad437078693811aa0674d0da9d3e1"
_PG_SUBS_HASH = "3a83766254ac9ac9984ec25cb73c6e010ea4418f5e35f143933e6b6e6473b921"
_PG_SCORES_HASH = "3fd7cdb5e78f1d43cabfabfeb6578c252b63af23ba2ab44db0094dc3a42de36d"
_HF_TRAIN_HASH = "681f0fe3cad9e2adabcd774ffaf5f40927e435e5b155af9ada146b1f1d733c6e"
_HF_TEST_HASH = "7256a7dafabe8a63270fef8e9b05d6d0e5711b3dc34f99ee4a1ad5e537d38776"
_SKEMPI_HASH = "76f8e60d09eaa4f05fb265063886859a86895c0b2fb225e31fe82928a883972d"
_PPIREF_HASH = "f0b026d644c5afea295b8c5e8e2bfdd501d7ed72cd25c9cc3b360306ef29fde7"
_PFAM_HASH = "2d82087b6c5c60d762cc767f98e8260b273134c215ab7efccf7440614a4e5dab"
_CHAINS_HASH = "08963f5fb73c02892a5d1e12b39795ef44ea50771453b80eecfe6f9e5033f03a"


# --- R3: OverfitNN homology inflation (metric_audit) --------------------------


def _r3(
    split: str,
    reported: float,
    r_lo: float,
    r_hi: float,
    honest: float,
    h_lo: float,
    h_hi: float,
    delta: float,
    d_lo: float,
    d_hi: float,
    leaked: int,
    hi_bucket: float,
    hi_n: int,
    lo_bucket: float,
    lo_n: int,
    lo_silent: bool,
) -> AuditReport:
    axis = "identity_to_nearest_reference"
    return assemble_report(
        benchmark_name=f"gosai_k562_overfitnn_{split}",
        reported=_metric(MetricName.SPEARMAN.value, reported, r_lo, r_hi, "prov:reported"),
        honest=_metric(MetricName.SPEARMAN.value, honest, h_lo, h_hi, "prov:honest"),
        delta=_metric("spearman_delta", delta, d_lo, d_hi, "prov:delta"),
        leakage=LeakageSummary(n_eval=5000, n_contaminated=leaked, per_detector={"mmseqs": leaked}),
        provenance=ProvenanceRecord(
            input_hashes={"dataset:regulatory_dna_gosai:evaluator_data.zip": _GOSAI_HASH},
            params={"identity_threshold": 0.80, "n_train": 20000, "n_test": 5000, "split": split},
            seed=_SEED,
            pinned_versions={"mmseqs": "18.8cc5c"},
            runtime_versions={"mmseqs": "18.8cc5c"},
        ),
        prefilter_enabled=False,
        stratification=(
            _stratum(axis, 0, "[0.0, 0.25)", lo_bucket, lo_n, silent=lo_silent),
            _stratum(axis, 3, "[0.75, 1.0)", hi_bucket, hi_n, silent=False),
        ),
    )


def r3_random_report() -> AuditReport:
    return _r3(
        "random_split",
        0.165,
        0.137,
        0.196,
        0.018,
        -0.016,
        0.050,
        0.147,
        0.107,
        0.186,
        1230,
        0.352,
        1230,
        0.018,
        3770,
        lo_silent=True,
    )


def r3_chr8_chr9_report() -> AuditReport:
    return _r3(
        "chr8_chr9_holdout",
        0.074,
        0.046,
        0.103,
        0.030,
        0.002,
        0.056,
        0.044,
        0.009,
        0.079,
        828,
        0.147,
        828,
        0.030,
        4172,
        lo_silent=False,
    )


# --- ProteinGym: MSA-depth stratification (stratification) --------------------


def proteingym_report() -> AuditReport:
    axis = "metadata:MSA_Neff_L_category"
    return assemble_stratification_report(
        benchmark_name="proteingym_esm1v_msa_depth",
        stratification=(
            _stratum(axis, 0, "Low", 0.298, 15, silent=False),
            _stratum(axis, 1, "Medium", 0.384, 15, silent=False),
            _stratum(axis, 2, "High", 0.531, 15, silent=False),
        ),
        provenance=ProvenanceRecord(
            input_hashes={
                "dataset:proteingym_dms:DMS_ProteinGym_substitutions.zip": _PG_SUBS_HASH,
                "dataset:proteingym_dms:zero_shot_substitutions_scores.zip": _PG_SCORES_HASH,
            },
            params={
                "baseline": "ESM1v_ensemble",
                "metric": "mean_per_assay_spearman",
                "n_per_bucket": 15,
            },
            seed=_SEED,
            pinned_versions={},
            runtime_versions={},
        ),
        limitations=(
            Limitation(
                id="proteingym_correlational",
                title="Correlational, with wide within-bucket overlap",
                detail=(
                    "The MSA-depth gradient is correlational, not causal: depth correlates with "
                    "protein family / organism / assay-type, and the within-bucket spread is wide "
                    "with overlapping ranges. The gradient is a shift in the mean, not clean "
                    "separation of buckets."
                ),
            ),
        ),
    )


# --- R2: reverse-complement leakage (detection, one split) --------------------


def r2_genomic_report() -> AuditReport:
    return assemble_detection_report(
        benchmark_name="hashfrag_gosai_reverse_complement",
        splits=(
            LeakageSplit(
                split_name="hashFrag example naive split",
                role=SplitRole.FINDING,
                cells=(
                    DetectorCell(
                        detector="sequence",
                        n_flagged=1616,
                        n_total=2000,
                        threshold_label="mmseqs both-strand, exact reverse-complement",
                    ),
                ),
                note="80.8% of test sequences are exact reverse-complements of training sequences.",
            ),
        ),
        provenance=ProvenanceRecord(
            input_hashes={
                "dataset:regulatory_dna_hashfrag:example_train_split.fa": _HF_TRAIN_HASH,
                "dataset:regulatory_dna_hashfrag:example_test_split.fa": _HF_TEST_HASH,
            },
            params={"strand_mode": "both", "match": "exact_reverse_complement"},
            seed=_SEED,
            pinned_versions={"mmseqs": "18.8cc5c"},
            runtime_versions={"mmseqs": "18.8cc5c"},
        ),
    )


# --- PPI: interface leakage splits-matrix (detection, four splits) ------------

_PPI_THRESHOLDS = {
    "sequence": "id>=0.30, cov>=0.50",
    "family": "Pfam e<=1e-3",
    "structural": "foldseek TM>=0.50",
}


def _ppi_split(
    name: str, role: SplitRole, total: int, seq: int, fam: int, struct: int, note: str | None = None
) -> LeakageSplit:
    return LeakageSplit(
        split_name=name,
        role=role,
        cells=(
            DetectorCell(
                detector="sequence",
                n_flagged=seq,
                n_total=total,
                threshold_label=_PPI_THRESHOLDS["sequence"],
            ),
            DetectorCell(
                detector="family",
                n_flagged=fam,
                n_total=total,
                threshold_label=_PPI_THRESHOLDS["family"],
            ),
            DetectorCell(
                detector="structural",
                n_flagged=struct,
                n_total=total,
                threshold_label=_PPI_THRESHOLDS["structural"],
            ),
        ),
        note=note,
    )


def ppi_report() -> AuditReport:
    return assemble_detection_report(
        benchmark_name="ppi_skempi_interface",
        splits=(
            _ppi_split(
                "demonstration (MMseqs2-30%)",
                SplitRole.DEMONSTRATION,
                52,
                0,
                18,
                20,
                note="Sequence split leaves family + fold-level structural leakage.",
            ),
            _ppi_split(
                "Pr/PI control (published)",
                SplitRole.CONTROL,
                60,
                0,
                0,
                2,
                note="Independent of the immune set: near-zero on all detectors.",
            ),
            _ppi_split(
                "AB/AG hold-out",
                SplitRole.FINDING,
                53,
                48,
                52,
                51,
                note="Shared immunoglobulin domains -> heavy leakage.",
            ),
            _ppi_split(
                "TCR/pMHC hold-out",
                SplitRole.FINDING,
                38,
                33,
                38,
                38,
                note="Shared immunoglobulin domains -> heavy leakage.",
            ),
        ),
        provenance=ProvenanceRecord(
            input_hashes={
                "dataset:ppi_bushuiev:skempi_v2.csv": _SKEMPI_HASH,
                "dataset:ppi_bushuiev:skempi2.zip": _PPIREF_HASH,
                "dataset:ppi_bushuiev:Pfam-A.hmm.gz": _PFAM_HASH,
                "dataset:ppi_bushuiev:vendored/chains.fasta": _CHAINS_HASH,
            },
            params={
                "split_construction": "mmseqs easy-search id>=0.30/cov>=0.50; components; seed 1729"
            },
            seed=_SEED,
            pinned_versions={"mmseqs": "18.8cc5c", "foldseek": "10.941cd33", "pyhmmer": "0.12.1"},
            runtime_versions={"mmseqs": "18.8cc5c", "foldseek": "10.941cd33", "pyhmmer": "0.12.1"},
        ),
        limitations=(_FOLD_LEVEL_CAVEAT,),
    )


def all_fixtures() -> dict[str, AuditReport]:
    """Fixture filename (stem) -> report. The viewer + gates consume these by name."""
    return {
        "r3_random": r3_random_report(),
        "r3_chr8_chr9": r3_chr8_chr9_report(),
        "proteingym_msa_depth": proteingym_report(),
        "r2_reverse_complement": r2_genomic_report(),
        "ppi_interface": ppi_report(),
    }
