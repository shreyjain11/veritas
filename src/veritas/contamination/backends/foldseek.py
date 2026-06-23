"""foldseek structural-search backend + its output parser."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

from veritas.contamination.executables import resolve_executable
from veritas.contamination.hits import StructuralHit
from veritas.contamination.subprocess_runner import CommandRunner, run_command
from veritas.contracts import EvalItem, ReferenceItem

# Request the CALIBRATED TM-score fields (qtmscore/ttmscore, both <= 1.0), NOT alntmscore
# (which exceeds 1.0 for strong/identical matches -- not a true TM-score). Paired with
# --alignment-type 1 (TMalign) so the score is a real structural-superposition TM-score.
_FORMAT_OUTPUT = "query,target,qtmscore,ttmscore,evalue"


def parse_foldseek(text: str) -> list[StructuralHit]:
    hits: list[StructuralHit] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        # tm_score = max(qtmscore, ttmscore): the TM normalized by the shorter chain (the
        # standard "same fold" convention; recall-oriented for an auditor).
        hits.append(
            StructuralHit(
                eval_id=parts[0], ref_id=parts[1], tm_score=max(float(parts[2]), float(parts[3]))
            )
        )
    return hits


def _resolve_id(raw: str, known: frozenset[str]) -> str:
    # foldseek emits one entry per chain, naming it "<id>_<chain>" (extension already removed;
    # older builds emitted "<id>.pdb_<chain>"). Resolve back to the item id we wrote: an exact
    # match (single-chain "<id>"), else the stem with the trailing "_<chain>" removed.
    candidate = raw.split(".pdb")[0]
    if candidate in known:
        return candidate
    stem = candidate.rsplit("_", 1)[0]
    if stem in known:
        return stem
    return candidate


class FoldseekSearch:
    def __init__(
        self,
        *,
        binary: str = "foldseek",
        runner: CommandRunner = run_command,
        timeout: float = 600.0,
    ) -> None:
        self._binary_name = binary
        self.binary_path = resolve_executable(binary)  # absolute path resolved once, here
        self._runner = runner
        self._timeout = timeout

    def version(self) -> str:
        binary = self.binary_path or self._binary_name
        result = self._runner([binary, "version"], cwd=Path.cwd(), timeout=self._timeout)
        return (result.stdout or result.stderr).strip()

    def search(
        self, eval_items: Sequence[EvalItem], reference_items: Sequence[ReferenceItem]
    ) -> list[StructuralHit]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            query_dir, target_dir = tmp / "query", tmp / "target"
            query_dir.mkdir()
            target_dir.mkdir()
            for eval_item in eval_items:
                assert eval_item.structure_path is not None
                shutil.copy(eval_item.structure_path, query_dir / f"{eval_item.id}.pdb")
            for ref_item in reference_items:
                assert ref_item.structure_path is not None
                shutil.copy(ref_item.structure_path, target_dir / f"{ref_item.id}.pdb")
            out = tmp / "result.tsv"
            binary = self.binary_path or self._binary_name
            self._runner(
                [
                    binary,
                    "easy-search",
                    str(query_dir),
                    str(target_dir),
                    str(out),
                    str(tmp / "foldseek_tmp"),
                    "--alignment-type",
                    "1",
                    "--format-output",
                    _FORMAT_OUTPUT,
                ],
                cwd=tmp,
                timeout=self._timeout,
            )
            raw_hits = parse_foldseek(out.read_text())
        eval_known = frozenset(item.id for item in eval_items)
        ref_known = frozenset(item.id for item in reference_items)
        return [
            StructuralHit(
                eval_id=_resolve_id(hit.eval_id, eval_known),
                ref_id=_resolve_id(hit.ref_id, ref_known),
                tm_score=hit.tm_score,
            )
            for hit in raw_hits
        ]
