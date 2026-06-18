"""In-process family search via pyhmmer (no external HMMER binary required)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pyhmmer
from pyhmmer.easel import Alphabet, DigitalSequenceBlock, TextSequence
from pyhmmer.plan7 import HMM, Background, Builder

from veritas.contamination.hits import FamilyAssignment
from veritas.contracts import EvalItem, ReferenceItem


def _as_str(value: str | bytes) -> str:
    return value.decode("ascii") if isinstance(value, bytes) else value


class PyhmmerSearch:
    def __init__(self, hmms: tuple[HMM, ...] = ()) -> None:
        self._hmms = hmms
        self._alphabet = Alphabet.amino()

    @classmethod
    def from_alignment(cls, path: Path, *, family_name: str) -> PyhmmerSearch:
        """Build a profile HMM from a multiple-sequence alignment (e.g. a Pfam seed)."""
        alphabet = Alphabet.amino()
        with pyhmmer.easel.MSAFile(
            str(path), format="afa", digital=True, alphabet=alphabet
        ) as handle:
            msa = handle.read()
        msa.name = family_name.encode("ascii")
        hmm, _profile, _optimized = Builder(alphabet).build_msa(msa, Background(alphabet))
        return cls(hmms=(hmm,))

    def version(self) -> str:
        return str(pyhmmer.__version__)

    def write_hmm(self, path: Path) -> None:
        with path.open("wb") as handle:
            for hmm in self._hmms:
                hmm.write(handle)

    def assign(self, items: Sequence[EvalItem | ReferenceItem]) -> list[FamilyAssignment]:
        if not self._hmms:
            return []
        sequences = [
            TextSequence(name=item.id.encode("ascii"), sequence=item.sequence).digitize(
                self._alphabet
            )
            for item in items
        ]
        block = DigitalSequenceBlock(self._alphabet, sequences)
        assignments: list[FamilyAssignment] = []
        for top_hits in pyhmmer.hmmer.hmmsearch(self._hmms, block):
            family = _as_str(top_hits.query.name)
            for hit in top_hits:
                assignments.append(
                    FamilyAssignment(item_id=_as_str(hit.name), family=family, e_value=hit.evalue)
                )
        return assignments
