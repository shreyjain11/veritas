"""Hermetic FoldseekSearch tests (fake runner, no binary).

These guard the two bugs the PPI demo surfaced and that the binary differential
tests missed:

  1. ID stripping: foldseek emits per-chain ids as ``<name>_<chain>`` (the ``.pdb``
     extension already removed). The previous ``.pdb``-only strip was a no-op on this
     format, so multi-chain matches never collapsed back to the item id and every
     interface-level edge was silently dropped. We resolve ids against the known item
     ids, so single-chain (``<id>``), multi-chain (``<id>_<chain>``), and the older
     ``<id>.pdb_<chain>`` formats all map back to ``<id>``.
  2. Calibrated score + invocation: the backend must request the calibrated TM fields
     (``qtmscore``/``ttmscore``, both <= 1.0) and run ``--alignment-type 1`` (TMalign),
     NOT the uncalibrated ``alntmscore`` (which exceeds 1.0 for strong matches).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from veritas.contamination.backends.foldseek import FoldseekSearch
from veritas.contamination.subprocess_runner import CommandResult
from veritas.contracts import EvalItem, ReferenceItem, SeqType


class _FakeFoldseekRunner:
    """Records argv and writes a foldseek-format result.tsv to the out path (argv[4])."""

    def __init__(self, rows: str) -> None:
        self.argv: list[str] = []
        self._rows = rows

    def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
        input_text: str | None = None,
    ) -> CommandResult:
        self.argv = list(argv)
        Path(argv[4]).write_text(self._rows)
        return CommandResult(stdout="", stderr="", returncode=0)


def _items(tmp_path: Path) -> tuple[tuple[EvalItem, ...], tuple[ReferenceItem, ...]]:
    eval_ids = ("1A22_A_B", "e_single")
    ref_ids = ("3MZG_A_B",)
    for i in (*eval_ids, *ref_ids):
        (tmp_path / f"{i}.pdb").write_text("REMARK fake\n")
    evals = tuple(
        EvalItem(
            id=i,
            sequence="MKVLA",
            seq_type=SeqType.PROTEIN,
            label=0.0,
            structure_path=tmp_path / f"{i}.pdb",
        )
        for i in eval_ids
    )
    refs = tuple(
        ReferenceItem(
            id=i, sequence="MKVLA", seq_type=SeqType.PROTEIN, structure_path=tmp_path / f"{i}.pdb"
        )
        for i in ref_ids
    )
    return evals, refs


def test_foldseek_invocation_requests_calibrated_tm_and_tmalign(tmp_path: Path) -> None:
    runner = _FakeFoldseekRunner("")
    evals, refs = _items(tmp_path)
    FoldseekSearch(runner=runner).search(evals, refs)
    argv = runner.argv
    assert "--alignment-type" in argv and argv[argv.index("--alignment-type") + 1] == "1"
    fmt = argv[argv.index("--format-output") + 1]
    assert fmt == "query,target,qtmscore,ttmscore,evalue"
    assert "alntmscore" not in fmt  # the uncalibrated field must not be used


def test_foldseek_multichain_ids_resolve_to_item_ids(tmp_path: Path) -> None:
    # foldseek appends "_<chain>" to each id; resolution must map back to the interface id.
    rows = (
        "1A22_A_B_A\t3MZG_A_B_A\t0.80\t0.70\t1e-9\n"  # both multi-chain -> 1A22_A_B / 3MZG_A_B
        "e_single\t3MZG_A_B_B\t0.60\t0.65\t1e-5\n"  # single-chain eval is exact; ref multi-chain
    )
    runner = _FakeFoldseekRunner(rows)
    evals, refs = _items(tmp_path)
    hits = FoldseekSearch(runner=runner).search(evals, refs)
    resolved = {(h.eval_id, h.ref_id): h.tm_score for h in hits}
    assert resolved == {
        ("1A22_A_B", "3MZG_A_B"): 0.80,  # tm = max(qtm 0.80, ttm 0.70)
        ("e_single", "3MZG_A_B"): 0.65,  # tm = max(qtm 0.60, ttm 0.65)
    }


def test_foldseek_unresolvable_id_falls_back_to_raw(tmp_path: Path) -> None:
    runner = _FakeFoldseekRunner("ghost_z\t3MZG_A_B_A\t0.55\t0.50\t1e-4\n")
    evals, refs = _items(tmp_path)
    hits = FoldseekSearch(runner=runner).search(evals, refs)
    # "ghost_z" matches no known eval id (nor stem "ghost") -> kept as-is.
    assert hits[0].eval_id == "ghost_z"
    assert hits[0].ref_id == "3MZG_A_B"
