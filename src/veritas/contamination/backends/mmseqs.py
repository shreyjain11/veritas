"""mmseqs2 sequence-search backend (primary) + its m8 output parser."""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from veritas.contamination.backends._common import to_fasta
from veritas.contamination.executables import resolve_executable
from veritas.contamination.hits import SequenceHit
from veritas.contamination.subprocess_runner import CommandRunner, run_command
from veritas.contracts import EvalItem, ReferenceItem, SeqType

# query,target,fident(0..1),qcov(0..1),tcov(0..1),evalue,bits
_FORMAT_OUTPUT = "query,target,fident,qcov,tcov,evalue,bits"


def parse_m8(text: str) -> list[SequenceHit]:
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
                identity=float(parts[2]),
                coverage=min(float(parts[3]), float(parts[4])),
            )
        )
    return hits


class MmseqsSearch:
    def __init__(
        self, *, binary: str = "mmseqs", runner: CommandRunner = run_command, timeout: float = 600.0
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
            query, target, out = tmp / "query.fasta", tmp / "target.fasta", tmp / "result.m8"
            query.write_text(to_fasta(eval_items))
            target.write_text(to_fasta(reference_items))
            binary = self.binary_path or self._binary_name
            argv = [
                binary,
                "easy-search",
                str(query),
                str(target),
                str(out),
                str(tmp / "mmseqs_tmp"),
                "--format-output",
                _FORMAT_OUTPUT,
            ]
            # mmseqs refuses to guess the alphabet: nucleotide search must be requested
            # explicitly (protein is the default, so it needs no flag).
            if eval_items and eval_items[0].seq_type is SeqType.NUCLEOTIDE:
                argv += ["--search-type", "3"]
            self._runner(argv, cwd=tmp, timeout=self._timeout)
            hits = parse_m8(out.read_text())
        return [hit for hit in hits if (hit.eval_id, hit.ref_id) in candidate_pairs]
