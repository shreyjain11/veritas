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

_FORMAT_OUTPUT = "query,target,alntmscore,evalue"


def parse_foldseek(text: str) -> list[StructuralHit]:
    hits: list[StructuralHit] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        hits.append(StructuralHit(eval_id=parts[0], ref_id=parts[1], tm_score=float(parts[2])))
    return hits


def _strip_structure_suffix(name: str) -> str:
    # foldseek identifies structures by filename (e.g. "e_close.pdb" or "e_close.pdb_A").
    return name.split(".pdb")[0]


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
                    "--format-output",
                    _FORMAT_OUTPUT,
                ],
                cwd=tmp,
                timeout=self._timeout,
            )
            raw_hits = parse_foldseek(out.read_text())
        return [
            StructuralHit(
                eval_id=_strip_structure_suffix(hit.eval_id),
                ref_id=_strip_structure_suffix(hit.ref_id),
                tm_score=hit.tm_score,
            )
            for hit in raw_hits
        ]
