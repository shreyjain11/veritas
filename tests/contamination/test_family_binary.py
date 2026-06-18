"""Differential test for the family detector: pyhmmer (in-process) vs the raw HMMER binary.

Marked ``requires_hmmer`` (auto-skipped offline). Both paths use the same HMM
built from the vendored seed alignment; their per-sequence family assignments
must agree.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from veritas.contamination.backends.hmmer import parse_domtblout
from veritas.contamination.backends.pyhmmer_search import PyhmmerSearch
from veritas.contracts import EvalItem, SeqType

pytestmark = pytest.mark.requires_hmmer

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "contamination"
_MEMBER = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKA"
_DECOY = "WWWWCCCCDDDDEEEEFFFFGGGGHHHHIIIIKKKKLLLLMMMMNNNNPPPPQQQQRRRRSS"


def test_pyhmmer_assignments_match_raw_hmmsearch(tmp_path: Path) -> None:
    search = PyhmmerSearch.from_alignment(_FIXTURES / "family_seed.afa", family_name="FamX")
    items = (
        EvalItem(id="member", sequence=_MEMBER, seq_type=SeqType.PROTEIN, label=1.0),
        EvalItem(id="decoy", sequence=_DECOY, seq_type=SeqType.PROTEIN, label=0.0),
    )
    pyhmmer_assignments = {(a.item_id, a.family) for a in search.assign(items) if a.e_value <= 1e-3}

    # Raw HMMER path on the same HMM and sequences.
    hmm_path = tmp_path / "FamX.hmm"
    search.write_hmm(hmm_path)
    seqs_path = tmp_path / "seqs.fasta"
    seqs_path.write_text(f">member\n{_MEMBER}\n>decoy\n{_DECOY}\n")
    domtbl = tmp_path / "out.domtblout"
    subprocess.run(
        ["hmmsearch", "--domtblout", str(domtbl), str(hmm_path), str(seqs_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    raw_assignments = {
        (a.item_id, a.family) for a in parse_domtblout(domtbl.read_text()) if a.e_value <= 1e-3
    }

    assert pyhmmer_assignments == raw_assignments
    assert ("member", "FamX") in pyhmmer_assignments
    assert ("decoy", "FamX") not in pyhmmer_assignments
