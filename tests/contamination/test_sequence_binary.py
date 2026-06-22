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
from collections.abc import Sequence
from pathlib import Path

import pytest

from veritas.contamination.backends.diamond import DiamondSearch
from veritas.contamination.backends.mmseqs import MmseqsSearch, parse_m8
from veritas.contamination.graph import contaminated_eval_ids
from veritas.contamination.sequence_identity import SequenceIdentityDetector
from veritas.contamination.subprocess_runner import CommandResult
from veritas.contracts import DetectorConfig, DetectorKind, EvalItem, ReferenceItem, SeqType
from veritas.io.fasta import read_fasta

# A short genomic window for the HERMETIC argv tests (the fake runner never invokes mmseqs,
# so its content is irrelevant).
_DNA_DUP = (
    "GTAGGCTCACCCATGCCTTTGGGTTTCCTGGACCTCCCCTTGGGAGGATGGCTCTGCAGAGGGG"
    "CTTTAATGTGAGATGTGAGCTCCTCACCACTGGGGG"
)

# Binary-backed nucleotide tests use REAL 200 bp genomic windows from the committed (MIT)
# hashFrag slice -- mmseqs nucleotide search is fragile on tiny/short synthetic inputs
# (it failed on Linux CI for short fragments), so we feed it realistic 200 bp sequences.
_VENDORED_DNA = (
    Path(__file__).resolve().parents[2]
    / "demos/regulatory_dna_hashfrag/vendored/example_test_split.fa"
)


def _real_dna(n: int) -> list[str]:
    return [
        record.sequence for record in read_fasta(_VENDORED_DNA, seq_type=SeqType.NUCLEOTIDE)[:n]
    ]


class _CapturingRunner:
    """Fake runner: records argv and writes an empty .m8 so parse_m8 succeeds (no binary)."""

    def __init__(self) -> None:
        self.argv: list[str] = []

    def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
        input_text: str | None = None,
    ) -> CommandResult:
        self.argv = list(argv)
        Path(argv[4]).write_text("")  # argv[4] is the result .m8 path
        return CommandResult(stdout="", stderr="", returncode=0)


def test_mmseqs_uses_nucleotide_search_type_for_dna() -> None:
    runner = _CapturingRunner()
    evals = (EvalItem(id="e1", sequence=_DNA_DUP, seq_type=SeqType.NUCLEOTIDE, label=0.0),)
    refs = (ReferenceItem(id="r1", sequence=_DNA_DUP, seq_type=SeqType.NUCLEOTIDE),)
    MmseqsSearch(runner=runner).search(evals, refs, candidate_pairs={("e1", "r1")})
    assert "--search-type" in runner.argv
    assert runner.argv[runner.argv.index("--search-type") + 1] == "3"


def test_mmseqs_omits_search_type_for_protein() -> None:
    runner = _CapturingRunner()
    evals = (EvalItem(id="e1", sequence=_REF1, seq_type=SeqType.PROTEIN, label=0.0),)
    refs = (ReferenceItem(id="r1", sequence=_REF1, seq_type=SeqType.PROTEIN),)
    MmseqsSearch(runner=runner).search(evals, refs, candidate_pairs={("e1", "r1")})
    assert "--search-type" not in runner.argv  # protein is mmseqs' default


def test_mmseqs_omits_search_type_when_no_eval_items() -> None:
    runner = _CapturingRunner()
    MmseqsSearch(runner=runner).search((), (), candidate_pairs=set())
    assert "--search-type" not in runner.argv


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
def test_mmseqs_detects_nucleotide_duplicate() -> None:
    # End-to-end nucleotide search (needs --search-type 3) on real 200 bp genomic windows:
    # an exact DNA duplicate of a reference is found.
    seqs = _real_dna(5)
    dup = seqs[0]
    evals = (
        EvalItem(id="e_dup", sequence=dup, seq_type=SeqType.NUCLEOTIDE, label=1.0),
        EvalItem(id="e_other", sequence=seqs[1], seq_type=SeqType.NUCLEOTIDE, label=0.0),
    )
    refs = (
        ReferenceItem(id="r_dup", sequence=dup, seq_type=SeqType.NUCLEOTIDE),
        *(
            ReferenceItem(id=f"r{i}", sequence=s, seq_type=SeqType.NUCLEOTIDE)
            for i, s in enumerate(seqs[2:])
        ),
    )
    graph = SequenceIdentityDetector(search=MmseqsSearch(), use_prefilter=False).detect(
        evals, refs, _config(identity=0.9, coverage=0.8)
    )
    assert "e_dup" in contaminated_eval_ids(graph)  # exact duplicate of r_dup


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


@pytest.mark.requires_mmseqs
def test_mmseqs_differential_matches_raw_run_nucleotide(tmp_path: Path) -> None:
    # Guards the --search-type 3 fix: the detector's nucleotide path must agree with a raw
    # mmseqs run that ALSO passes --search-type 3. If the flag regressed, the wrapper would
    # die or diverge from raw and this differential would fail (it cannot regress silently).
    # Real 200 bp genomic windows; e_dup is an exact duplicate of r_dup.
    seqs = _real_dna(6)
    evals = {"e_dup": seqs[0], "e_a": seqs[1], "e_b": seqs[2]}
    refs = {"r_dup": seqs[0], "r_c": seqs[3], "r_d": seqs[4], "r_e": seqs[5]}
    query, target, out = tmp_path / "q.fasta", tmp_path / "t.fasta", tmp_path / "res.m8"
    query.write_text("".join(f">{k}\n{v}\n" for k, v in evals.items()))
    target.write_text("".join(f">{k}\n{v}\n" for k, v in refs.items()))
    proc = subprocess.run(
        [
            "mmseqs",
            "easy-search",
            str(query),
            str(target),
            str(out),
            str(tmp_path / "mmseqs_tmp"),
            "--search-type",
            "3",
            "--format-output",
            "query,target,fident,qcov,tcov,evalue,bits",
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:  # surface mmseqs' own diagnostic if it ever fails (e.g. on a runner)
        pytest.fail(f"raw mmseqs nucleotide search failed (rc={proc.returncode}):\n{proc.stderr}")
    raw_pairs = {
        (h.eval_id, h.ref_id)
        for h in parse_m8(out.read_text())
        if h.identity >= 0.9 and h.coverage >= 0.8
    }
    detector = SequenceIdentityDetector(search=MmseqsSearch(), use_prefilter=False)
    eval_items = tuple(
        EvalItem(id=k, sequence=v, seq_type=SeqType.NUCLEOTIDE, label=0.0) for k, v in evals.items()
    )
    ref_items = tuple(
        ReferenceItem(id=k, sequence=v, seq_type=SeqType.NUCLEOTIDE) for k, v in refs.items()
    )
    detector_pairs = {
        (e.eval_id, e.ref_id) for e in detector.detect(eval_items, ref_items, _config()).edges
    }
    assert detector_pairs == raw_pairs
    assert ("e_dup", "r_dup") in detector_pairs  # the planted nucleotide duplicate is found


@pytest.mark.requires_diamond
def test_diamond_golden_recovers_planted_duplicate() -> None:
    detector = SequenceIdentityDetector(
        search=DiamondSearch(), detector_id="diamond", use_prefilter=False
    )
    graph = detector.detect(_evals(), _refs(), _config())
    assert "e_dup" in contaminated_eval_ids(graph)
