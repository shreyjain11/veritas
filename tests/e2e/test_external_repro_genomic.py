"""(e) External reproduction R2 -- genomic reverse-complement leakage detection (hashFrag).

CLAIM (verified): On hashFrag's example naive split, Veritas detects that 80.8% (1616/2000)
of test sequences are exact reverse-complements of training sequences -- genuine same-element
homology. hashFrag handles reverse complements BY DEFAULT (it generates them when building its
BLAST database; controlled by --skip-revcomp). Its example/tutorial commands EXPLICITLY pass
--skip-revcomp, disabling that, because the example input already carries both orientations as
``_Reversed`` records -- so the example default removed 197 (9.85%), only 165 overlapping the
reverse-complement set, leaving ~1,450. Veritas performs both-strand detection by default and
surfaces reverse-complement homology a naive split leaves in: why post-hoc auditing catches
what split-creation defaults can miss.

This is NOT a claim that hashFrag-the-method is broken or its authors erred: it is the EXAMPLE
run with its DEFAULT flags (--skip-revcomp on the tutorial commands). Whether other hashFrag
configurations capture this is not assessed here.

Verified three ways: mmseqs both-strand search, reverse-complement string match, and overlap of
hashFrag's removed set with the reverse-complement set. The first (data) test below locks the
string-match + removed-set facts with no binary; the second confirms Veritas's both-strand
detector recovers the leakage (needs mmseqs + adequate memory).
"""

from __future__ import annotations

import gzip
import subprocess
from pathlib import Path

import pytest

from veritas.contamination.backends.mmseqs import MmseqsSearch
from veritas.contamination.graph import contaminated_eval_ids
from veritas.contamination.sequence_identity import SequenceIdentityDetector
from veritas.contracts import DetectorConfig, DetectorKind, EvalItem, ReferenceItem, SeqType
from veritas.io.fasta import FastaRecord, parse_fasta, read_fasta

_VENDORED = Path(__file__).resolve().parents[2] / "demos/regulatory_dna_hashfrag/vendored"

# hashFrag example removal with --skip-revcomp (its tutorial default): 197/2000.
_HASHFRAG_EXAMPLE_REMOVAL_RATE = 197 / 2000  # 0.0985
# Observed reverse-complement leakage (verified): 1616/2000 = 0.808. The detector floor is set
# well below it -- a regression guard, NOT the observed value.
_RC_LEAKAGE_FLOOR = 0.50
_IDENTITY, _COVERAGE = 0.80, 0.80


def _revcomp(seq: str) -> str:
    return seq.translate(str.maketrans("ACGT", "TGCA"))[::-1]


def _load(name: str) -> tuple[FastaRecord, ...]:
    path = _VENDORED / name
    if name.endswith(".gz"):
        return parse_fasta(gzip.decompress(path.read_bytes()).decode(), seq_type=SeqType.NUCLEOTIDE)
    return read_fasta(path, seq_type=SeqType.NUCLEOTIDE)


def test_reverse_complement_leakage_data_facts() -> None:
    # No binary: locks the verified data facts directly from the committed slice.
    train = _load("example_train_split.fa")
    test = _load("example_test_split.fa")
    filtered = _load("example_test_split.filtered.fa.gz")
    assert (len(train), len(test), len(filtered)) == (8000, 2000, 1803)  # removed = 197

    train_seqs = {r.sequence for r in train}
    train_rc = {_revcomp(r.sequence) for r in train}
    rc_hits = {r.id for r in test if r.sequence in train_rc}
    same_strand = sum(1 for r in test if r.sequence in train_seqs)
    assert same_strand == 0  # no exact same-strand duplicates
    assert len(rc_hits) == 1616  # 80.8% of test are exact reverse-complements of train

    removed_ids = {r.id for r in test} - {r.id for r in filtered}
    assert len(removed_ids) == 197  # hashFrag example default (--skip-revcomp) removal
    assert len(removed_ids & rc_hits) == 165  # only 165 of the removed are in the RC set
    # ~1,450 reverse-complement duplicates remain in hashFrag's example filtered split
    assert len(rc_hits - removed_ids) == 1616 - 165


@pytest.mark.external
@pytest.mark.requires_mmseqs
def test_veritas_both_strand_detector_recovers_rc_leakage() -> None:
    train = _load("example_train_split.fa")
    test = _load("example_test_split.fa")
    evals = tuple(
        EvalItem(id=r.id, sequence=r.sequence, seq_type=SeqType.NUCLEOTIDE, label=0.0) for r in test
    )
    refs = tuple(
        ReferenceItem(id=r.id, sequence=r.sequence, seq_type=SeqType.NUCLEOTIDE) for r in train
    )
    config = DetectorConfig(
        kind=DetectorKind.SEQUENCE,
        name="mmseqs",
        identity_threshold=_IDENTITY,
        coverage_threshold=_COVERAGE,
    )
    # Exhaustive (use_prefilter=False): the MinHash prefilter keys on FORWARD k-mers and would
    # miss reverse-complement homology, which mmseqs' both-strand search finds.
    try:
        graph = SequenceIdentityDetector(search=MmseqsSearch(), use_prefilter=False).detect(
            evals, refs, config
        )
    except subprocess.CalledProcessError as exc:
        if "Cannot fit databases" in (exc.stderr or ""):  # mmseqs nucleotide OOM on small runners
            pytest.skip(
                f"mmseqs nucleotide search needs more RAM than this machine has:\n{exc.stderr}"
            )
        raise

    eval_ids = {e.id for e in evals}
    leakage = len(contaminated_eval_ids(graph) & eval_ids) / len(eval_ids)
    assert leakage >= _RC_LEAKAGE_FLOOR  # observed 0.808; floor is a regression guard
    assert leakage > _HASHFRAG_EXAMPLE_REMOVAL_RATE  # far exceeds the example default's 9.85%
