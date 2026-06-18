"""diamond sequence-search backend (optional) + its BLAST-tab parser."""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from veritas.contamination.backends._common import to_fasta
from veritas.contamination.executables import resolve_executable
from veritas.contamination.hits import SequenceHit
from veritas.contamination.subprocess_runner import CommandRunner, run_command
from veritas.contracts import EvalItem, ReferenceItem

# qseqid sseqid pident(0..100) qcovhsp(0..100) scovhsp(0..100) evalue bitscore
_OUTFMT = ("6", "qseqid", "sseqid", "pident", "qcovhsp", "scovhsp", "evalue", "bitscore")


def parse_blast6(text: str) -> list[SequenceHit]:
    hits: list[SequenceHit] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        hits.append(
            SequenceHit(
                eval_id=parts[0],
                ref_id=parts[1],
                identity=float(parts[2]) / 100.0,
                coverage=min(float(parts[3]), float(parts[4])) / 100.0,
            )
        )
    return hits


class DiamondSearch:
    def __init__(
        self,
        *,
        binary: str = "diamond",
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
        self,
        eval_items: Sequence[EvalItem],
        reference_items: Sequence[ReferenceItem],
        *,
        candidate_pairs: set[tuple[str, str]],
    ) -> list[SequenceHit]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            query, ref = tmp / "query.fasta", tmp / "ref.fasta"
            db, out = tmp / "refdb", tmp / "out.tsv"
            query.write_text(to_fasta(eval_items))
            ref.write_text(to_fasta(reference_items))
            binary = self.binary_path or self._binary_name
            self._runner(
                [binary, "makedb", "--in", str(ref), "-d", str(db), "--quiet"],
                cwd=tmp,
                timeout=self._timeout,
            )
            self._runner(
                [
                    binary,
                    "blastp",
                    "-q",
                    str(query),
                    "-d",
                    str(db),
                    "-o",
                    str(out),
                    "--outfmt",
                    *_OUTFMT,
                    "--quiet",
                ],
                cwd=tmp,
                timeout=self._timeout,
            )
            hits = parse_blast6(out.read_text())
        return [hit for hit in hits if (hit.eval_id, hit.ref_id) in candidate_pairs]
