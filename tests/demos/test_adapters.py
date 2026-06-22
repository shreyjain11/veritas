"""Adapter mapping: raw dataset files -> Benchmark / EvalItem / ReferenceItem contracts.

These exercise the contract mapping + the reference-set semantics on tiny synthetic
fixtures shaped exactly like the real datasets (column names confirmed upstream). They
do NOT fetch real data or run audits -- that is the (later) full-tier step.

The reference-set wiring is the integrity crux and is asserted explicitly:
- ProteinGym: stratification-only; its reference wild-type is labelled benchmark
  REDUNDANCY, never model-training leakage.
- PPI / regulatory-DNA: the reference is the TRAIN split; ``seen_reason`` says so, and
  homology to it is the leakage signal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from veritas.contracts import MetricName, SeqType
from veritas.demos.ppi import PPIAdapter
from veritas.demos.proteingym import ProteinGymAdapter
from veritas.demos.regulatory_dna import RegulatoryDNAAdapter
from veritas.io.adapters import BenchmarkAdapter, ReferenceAdapter


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- ProteinGym


def _proteingym(tmp_path: Path) -> ProteinGymAdapter:
    reference = _write(
        tmp_path / "reference.csv",
        "DMS_id,UniProt_ID,target_seq,MSA_Neff_L_category\nASSAY1,P12345,MKVLAAGG,Low\n",
    )
    assay = _write(
        tmp_path / "assay.csv",
        "mutant,mutated_sequence,DMS_score,DMS_score_bin\n"
        "M1A,AKVLAAGG,1.5,1\nK2R,MRVLAAGG,-0.3,0\n",
    )
    scores = _write(tmp_path / "scores.csv", "mutant,score\nM1A,0.9\nK2R,0.2\n")
    return ProteinGymAdapter(
        assay_csv=assay, reference_csv=reference, scores_csv=scores, dms_id="ASSAY1"
    )


def test_proteingym_is_a_benchmark_and_reference_adapter(tmp_path: Path) -> None:
    adapter = _proteingym(tmp_path)
    assert isinstance(adapter, BenchmarkAdapter)
    assert isinstance(adapter, ReferenceAdapter)


def test_proteingym_maps_variants_with_msa_depth_metadata(tmp_path: Path) -> None:
    benchmark = _proteingym(tmp_path).load_benchmark()
    assert benchmark.metric.name is MetricName.SPEARMAN
    assert [item.id for item in benchmark.eval_items] == ["ASSAY1:M1A", "ASSAY1:K2R"]
    first = benchmark.eval_items[0]
    assert first.seq_type is SeqType.PROTEIN
    assert first.sequence == "AKVLAAGG"
    assert first.label == 1.5
    assert first.prediction == 0.9  # joined from the model scores file
    assert first.metadata["MSA_Neff_L_category"] == "Low"
    assert first.metadata["DMS_id"] == "ASSAY1"


def test_proteingym_reference_is_redundancy_not_leakage(tmp_path: Path) -> None:
    refs = _proteingym(tmp_path).load_reference()
    assert len(refs) == 1
    assert refs[0].sequence == "MKVLAAGG"  # the assay wild-type
    reason = refs[0].seen_reason or ""
    assert "redundancy" in reason.lower()
    assert "not model-training leakage" in reason.lower()


def test_proteingym_rejects_a_variant_without_a_model_score(tmp_path: Path) -> None:
    _proteingym(tmp_path)  # set up files
    _write(tmp_path / "scores.csv", "mutant,score\nM1A,0.9\n")  # drop K2R's score
    adapter = ProteinGymAdapter(
        assay_csv=tmp_path / "assay.csv",
        reference_csv=tmp_path / "reference.csv",
        scores_csv=tmp_path / "scores.csv",
        dms_id="ASSAY1",
    )
    with pytest.raises(ValueError, match="score"):
        adapter.load_benchmark()


def test_proteingym_rejects_an_unknown_assay_id(tmp_path: Path) -> None:
    adapter = _proteingym(tmp_path)
    other = ProteinGymAdapter(
        assay_csv=tmp_path / "assay.csv",
        reference_csv=tmp_path / "reference.csv",
        scores_csv=tmp_path / "scores.csv",
        dms_id="NOPE",
    )
    assert adapter.load_benchmark()  # the valid one works
    with pytest.raises(ValueError, match="NOPE"):
        other.load_reference()


# --------------------------------------------------------------------------------- PPI


def test_ppi_maps_eval_and_train_reference(tmp_path: Path) -> None:
    eval_csv = _write(
        tmp_path / "eval.csv",
        "id,sequence,label,prediction\ne1,MKVLAAGG,1,0.9\ne2,GGAAVLKM,0,0.2\n",
    )
    reference_csv = _write(tmp_path / "train.csv", "id,sequence\nr1,MKVLAAGG\n")
    adapter = PPIAdapter(eval_table=eval_csv, reference_table=reference_csv, benchmark_name="ppi")
    assert isinstance(adapter, BenchmarkAdapter)

    benchmark = adapter.load_benchmark()
    assert benchmark.metric.name is MetricName.AUROC
    assert benchmark.eval_items[0].seq_type is SeqType.PROTEIN
    assert benchmark.eval_items[0].label == 1.0

    refs = adapter.load_reference()
    assert refs[0].id == "r1"
    assert "train split" in (refs[0].seen_reason or "").lower()


def test_ppi_attaches_structure_paths_when_a_structures_dir_is_given(tmp_path: Path) -> None:
    eval_csv = _write(
        tmp_path / "eval.csv",
        "id,sequence,label,prediction,structure\ne1,MKVLAAGG,1,0.9,e1.pdb\n",
    )
    reference_csv = _write(tmp_path / "train.csv", "id,sequence,structure\nr1,MKVLAAGG,r1.pdb\n")
    adapter = PPIAdapter(
        eval_table=eval_csv, reference_table=reference_csv, structures_dir=tmp_path
    )
    item = adapter.load_benchmark().eval_items[0]
    assert item.structure_path == tmp_path / "e1.pdb"
    assert adapter.load_reference()[0].structure_path == tmp_path / "r1.pdb"


# --------------------------------------------------------------------- regulatory DNA


def test_regulatory_dna_maps_nucleotides_with_chromosome_metadata(tmp_path: Path) -> None:
    eval_csv = _write(
        tmp_path / "eval.csv",
        "id,sequence,label,prediction,chromosome\nd1,ACGTACGT,1,0.8,chr1\nd2,TTTTGGGG,0,0.1,chr2\n",
    )
    reference_csv = _write(tmp_path / "train.csv", "id,sequence\nt1,ACGTACGT\n")
    adapter = RegulatoryDNAAdapter(eval_table=eval_csv, reference_table=reference_csv)
    assert isinstance(adapter, BenchmarkAdapter)

    benchmark = adapter.load_benchmark()
    assert benchmark.metric.name is MetricName.AUROC
    item = benchmark.eval_items[0]
    assert item.seq_type is SeqType.NUCLEOTIDE
    assert item.metadata["chromosome"] == "chr1"

    refs = adapter.load_reference()
    assert refs[0].seq_type is SeqType.NUCLEOTIDE
    assert "train split" in (refs[0].seen_reason or "").lower()


def test_eval_table_missing_required_columns_is_rejected(tmp_path: Path) -> None:
    bad = _write(tmp_path / "eval.csv", "id,sequence,label\ne1,MKVLAAGG,1\n")  # no prediction
    reference_csv = _write(tmp_path / "train.csv", "id,sequence\nr1,MKVLAAGG\n")
    with pytest.raises(ValueError, match="prediction"):
        PPIAdapter(eval_table=bad, reference_table=reference_csv).load_benchmark()


def test_blank_structure_cell_yields_no_structure_path(tmp_path: Path) -> None:
    eval_csv = _write(
        tmp_path / "eval.csv",
        "id,sequence,label,prediction,structure\ne1,MKVLAAGG,1,0.9,\n",  # blank structure cell
    )
    reference_csv = _write(tmp_path / "train.csv", "id,sequence\nr1,MKVLAAGG\n")
    item = (
        PPIAdapter(eval_table=eval_csv, reference_table=reference_csv, structures_dir=tmp_path)
        .load_benchmark()
        .eval_items[0]
    )
    assert item.structure_path is None


def test_proteingym_rejects_a_reference_missing_columns(tmp_path: Path) -> None:
    _proteingym(tmp_path)
    _write(  # drop MSA_Neff_L_category
        tmp_path / "reference.csv", "DMS_id,UniProt_ID,target_seq\nASSAY1,P12345,MKVLAAGG\n"
    )
    adapter = ProteinGymAdapter(
        assay_csv=tmp_path / "assay.csv",
        reference_csv=tmp_path / "reference.csv",
        scores_csv=tmp_path / "scores.csv",
        dms_id="ASSAY1",
    )
    with pytest.raises(ValueError, match="required columns"):
        adapter.load_reference()


def test_proteingym_rejects_a_scores_file_missing_columns(tmp_path: Path) -> None:
    _proteingym(tmp_path)
    _write(tmp_path / "scores.csv", "mutant\nM1A\n")  # no score column
    adapter = ProteinGymAdapter(
        assay_csv=tmp_path / "assay.csv",
        reference_csv=tmp_path / "reference.csv",
        scores_csv=tmp_path / "scores.csv",
        dms_id="ASSAY1",
    )
    with pytest.raises(ValueError, match="required columns"):
        adapter.load_benchmark()


def test_proteingym_rejects_an_assay_missing_columns(tmp_path: Path) -> None:
    _proteingym(tmp_path)
    _write(tmp_path / "assay.csv", "mutant,mutated_sequence\nM1A,AKVLAAGG\n")  # no DMS_score
    adapter = ProteinGymAdapter(
        assay_csv=tmp_path / "assay.csv",
        reference_csv=tmp_path / "reference.csv",
        scores_csv=tmp_path / "scores.csv",
        dms_id="ASSAY1",
    )
    with pytest.raises(ValueError, match="required columns"):
        adapter.load_benchmark()
