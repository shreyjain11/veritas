"""Backend output parsers, tested on captured tool-output samples (no binary needed).

The exact column layouts here are the ones our detector invocations request; the
binary differential tests confirm the real tools still emit these formats.
"""

from __future__ import annotations

import pytest

from veritas.contamination.backends.diamond import parse_blast6
from veritas.contamination.backends.foldseek import parse_foldseek
from veritas.contamination.backends.hmmer import parse_domtblout
from veritas.contamination.backends.mmseqs import parse_m8
from veritas.contamination.hits import FamilyAssignment, SequenceHit, StructuralHit

# mmseqs easy-search --format-output "query,target,fident,qcov,tcov,evalue,bits"
_MMSEQS_M8 = (
    "e1\tr1\t1.000\t1.000\t1.000\t1.2E-30\t100.0\ne2\tr2\t0.850\t0.900\t0.880\t3.4E-10\t60.0\n"
)

# foldseek easy-search --alignment-type 1 --format-output "query,target,qtmscore,ttmscore,evalue"
# tm_score = max(qtmscore, ttmscore) -- the TM normalized by the shorter chain (standard
# "same fold" convention; recall-oriented for an auditor). Both fields are calibrated <= 1.0.
_FOLDSEEK = "e1\tr1\t0.950\t0.900\t1e-20\ne2\tr2\t0.250\t0.300\t0.1\n"

# hmmsearch --domtblout (whitespace-separated; leading comment lines start with '#').
# Columns: 1=target(sequence) ... 4=query(HMM/family) ... 7=full-seq E-value.
_DOMTBLOUT = (
    "# target name        accession  tlen query ...\n"
    "e1 - 300 PF00069 PF00069.1 250 1.2e-40 130.0 0.1 1 1 1.0e-43 1.2e-40 129.0 "
    "0.0 1 250 10 260 5 265 0.95 Protein kinase domain\n"
)


def test_parse_m8_maps_identity_and_coverage() -> None:
    hits = parse_m8(_MMSEQS_M8)
    assert hits == [
        SequenceHit(eval_id="e1", ref_id="r1", identity=1.0, coverage=1.0),
        SequenceHit(eval_id="e2", ref_id="r2", identity=0.85, coverage=0.88),
    ]


def test_parse_foldseek_maps_tm_score() -> None:
    hits = parse_foldseek(_FOLDSEEK)
    assert hits == [
        StructuralHit(eval_id="e1", ref_id="r1", tm_score=0.95),  # max(0.95, 0.90)
        StructuralHit(eval_id="e2", ref_id="r2", tm_score=0.30),  # max(0.25, 0.30)
    ]


def test_parse_domtblout_skips_comments_and_maps_assignment() -> None:
    assignments = parse_domtblout(_DOMTBLOUT)
    assert assignments == [FamilyAssignment(item_id="e1", family="PF00069", e_value=1.2e-40)]


def test_parse_m8_empty_input_yields_no_hits() -> None:
    assert parse_m8("") == []


# diamond blastp --outfmt 6 qseqid sseqid pident qcovhsp scovhsp evalue bitscore (percent units)
_DIAMOND_BLAST6 = "e1\tr1\t100.0\t100.0\t100.0\t1e-30\t200\ne2\tr2\t85.0\t90.0\t88.0\t1e-10\t120\n"


def test_parse_blast6_maps_percent_identity_and_coverage() -> None:
    assert parse_blast6(_DIAMOND_BLAST6) == [
        SequenceHit(eval_id="e1", ref_id="r1", identity=1.0, coverage=1.0),
        SequenceHit(eval_id="e2", ref_id="r2", identity=0.85, coverage=0.88),
    ]


@pytest.mark.parametrize("parser", [parse_m8, parse_foldseek, parse_blast6])
def test_sequence_like_parsers_ignore_blank_lines(parser: object) -> None:
    assert parser("\n\n") == []  # type: ignore[operator]
