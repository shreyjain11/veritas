"""End-to-end + differential tests for the sequence detector against the real binaries.

Marked ``requires_mmseqs`` / ``requires_diamond``: the conftest auto-skips these
when the binary is absent (offline dev), and CI runs them with the pinned tools.

Correctness tests run with ``use_prefilter=False`` so they exhaustively exercise
the detector over all eval x ref pairs. The MinHash prefilter is a scale
optimization whose recall is defined on k-mer Jaccard (not alignment identity)
and is tested separately; it must never sit between a correctness assertion and
the aligner (see test_prefilter / test_sequence_detector).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from veritas.contamination.backends.diamond import DiamondSearch
from veritas.contamination.backends.mmseqs import MmseqsSearch, parse_m8
from veritas.contamination.graph import contaminated_eval_ids
from veritas.contamination.sequence_identity import SequenceIdentityDetector
from veritas.contracts import DetectorConfig, DetectorKind, EvalItem, ReferenceItem, SeqType

# Two unrelated ~60aa proteins, plus a clearly non-homologous decoy.
_REF1 = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKA"
_REF2 = "MSEQDLHAPQWLNGTKVLVTGGSRGIGKAIALAFAEAGADVAINYRSDEAEANEVVAEIEA"
_UNRELATED = "WWWWCCCCDDDDEEEEFFFFGGGGHHHHIIIIKKKKLLLLMMMMNNNNPPPPQQQQRRRRSS"


def _config(identity: float = 0.9, coverage: float = 0.8) -> DetectorConfig:
    return DetectorConfig(
        kind=DetectorKind.SEQUENCE,
        name="mmseqs",
        identity_threshold=identity,
        coverage_threshold=coverage,
    )


def _evals() -> tuple[EvalItem, ...]:
    return (
        EvalItem(id="e_dup", sequence=_REF1, seq_type=SeqType.PROTEIN, label=1.0),
        EvalItem(id="e_unrel", sequence=_UNRELATED, seq_type=SeqType.PROTEIN, label=0.0),
    )


def _refs() -> tuple[ReferenceItem, ...]:
    return (
        ReferenceItem(id="r1", sequence=_REF1, seq_type=SeqType.PROTEIN),
        ReferenceItem(id="r2", sequence=_REF2, seq_type=SeqType.PROTEIN),
    )


@pytest.mark.requires_mmseqs
def test_mmseqs_golden_recovers_planted_duplicate() -> None:
    graph = SequenceIdentityDetector(search=MmseqsSearch(), use_prefilter=False).detect(
        _evals(), _refs(), _config()
    )
    contaminated = contaminated_eval_ids(graph)
    assert "e_dup" in contaminated  # exact duplicate of r1
    assert "e_unrel" not in contaminated


@pytest.mark.requires_mmseqs
def test_mmseqs_specificity_unrelated_yields_no_edges() -> None:
    evals = (EvalItem(id="e1", sequence=_UNRELATED, seq_type=SeqType.PROTEIN, label=0.0),)
    graph = SequenceIdentityDetector(search=MmseqsSearch(), use_prefilter=False).detect(
        evals, _refs(), _config()
    )
    assert graph.edges == ()


@pytest.mark.requires_mmseqs
def test_mmseqs_reports_runtime_version() -> None:
    assert MmseqsSearch().version()


@pytest.mark.requires_mmseqs
def test_mmseqs_differential_matches_raw_run(tmp_path: Path) -> None:
    evals = {"e_dup": _REF1, "e_unrel": _UNRELATED}
    refs = {"r1": _REF1, "r2": _REF2}
    query = tmp_path / "q.fasta"
    target = tmp_path / "t.fasta"
    query.write_text("".join(f">{k}\n{v}\n" for k, v in evals.items()))
    target.write_text("".join(f">{k}\n{v}\n" for k, v in refs.items()))
    out = tmp_path / "res.m8"
    subprocess.run(
        [
            "mmseqs",
            "easy-search",
            str(query),
            str(target),
            str(out),
            str(tmp_path / "mmseqs_tmp"),
            "--format-output",
            "query,target,fident,qcov,tcov,evalue,bits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    raw_pairs = {
        (h.eval_id, h.ref_id)
        for h in parse_m8(out.read_text())
        if h.identity >= 0.9 and h.coverage >= 0.8
    }
    detector = SequenceIdentityDetector(search=MmseqsSearch(), use_prefilter=False)
    eval_items = tuple(
        EvalItem(id=k, sequence=v, seq_type=SeqType.PROTEIN, label=0.0) for k, v in evals.items()
    )
    ref_items = tuple(
        ReferenceItem(id=k, sequence=v, seq_type=SeqType.PROTEIN) for k, v in refs.items()
    )
    detector_pairs = {
        (e.eval_id, e.ref_id) for e in detector.detect(eval_items, ref_items, _config()).edges
    }
    assert detector_pairs == raw_pairs


@pytest.mark.requires_diamond
def test_diamond_golden_recovers_planted_duplicate() -> None:
    detector = SequenceIdentityDetector(
        search=DiamondSearch(), detector_id="diamond", use_prefilter=False
    )
    graph = detector.detect(_evals(), _refs(), _config())
    assert "e_dup" in contaminated_eval_ids(graph)
