"""FASTA parsing: golden parse, multiline join, order, alphabet, malformed input."""

from __future__ import annotations

from pathlib import Path

import pytest

from veritas.contracts import SeqType
from veritas.io import FastaRecord, parse_fasta, read_fasta

PROTEIN_FASTA = ">e1 first\nMKVLA\n>e2\nGGGSS\n"
NUCLEOTIDE_FASTA = ">n1\nACGT\nACGT\n>n2\nTTTT\n"


def test_parse_protein_fasta_golden() -> None:
    records = parse_fasta(PROTEIN_FASTA, seq_type=SeqType.PROTEIN)
    assert records == (
        FastaRecord(id="e1", description="first", sequence="MKVLA"),
        FastaRecord(id="e2", description="", sequence="GGGSS"),
    )


def test_multiline_sequence_is_joined() -> None:
    records = parse_fasta(NUCLEOTIDE_FASTA, seq_type=SeqType.NUCLEOTIDE)
    assert records[0].sequence == "ACGTACGT"


def test_order_is_preserved() -> None:
    records = parse_fasta(PROTEIN_FASTA, seq_type=SeqType.PROTEIN)
    assert [r.id for r in records] == ["e1", "e2"]


def test_sequences_uppercased() -> None:
    records = parse_fasta(">x\nmkv\n", seq_type=SeqType.PROTEIN)
    assert records[0].sequence == "MKV"


def test_rejects_invalid_character() -> None:
    with pytest.raises(ValueError):
        parse_fasta(">x\nMK1\n", seq_type=SeqType.PROTEIN)


def test_rejects_sequence_before_header() -> None:
    with pytest.raises(ValueError):
        parse_fasta("MKV\n>x\nMKV\n", seq_type=SeqType.PROTEIN)


def test_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError):
        parse_fasta(">x\nMKV\n>x\nGGG\n", seq_type=SeqType.PROTEIN)


def test_rejects_empty_input() -> None:
    with pytest.raises(ValueError):
        parse_fasta("", seq_type=SeqType.PROTEIN)


def test_read_fasta_from_file_matches_parse(tmp_path: Path) -> None:
    path = tmp_path / "seqs.fasta"
    path.write_text(PROTEIN_FASTA)
    assert read_fasta(path, seq_type=SeqType.PROTEIN) == parse_fasta(
        PROTEIN_FASTA, seq_type=SeqType.PROTEIN
    )


def test_blank_lines_are_skipped() -> None:
    records = parse_fasta(">e1\nMKV\n\n>e2\nGGG\n", seq_type=SeqType.PROTEIN)
    assert [r.id for r in records] == ["e1", "e2"]


def test_rejects_empty_header_id() -> None:
    with pytest.raises(ValueError):
        parse_fasta(">\nMKV\n", seq_type=SeqType.PROTEIN)


def test_rejects_record_without_sequence() -> None:
    with pytest.raises(ValueError):
        parse_fasta(">x\n>y\nMKV\n", seq_type=SeqType.PROTEIN)
