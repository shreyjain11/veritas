"""Deterministic FASTA parsing for protein and nucleotide sequences."""

from __future__ import annotations

from pathlib import Path

from veritas.contracts.base import FrozenModel
from veritas.contracts.enums import SeqType
from veritas.contracts.sequences import normalize_sequence


class FastaRecord(FrozenModel):
    id: str
    description: str
    sequence: str


def parse_fasta(text: str, *, seq_type: SeqType) -> tuple[FastaRecord, ...]:
    """Parse FASTA text into records, preserving input order.

    Raises :class:`ValueError` on malformed input: a header without an id,
    sequence data before any header, duplicate ids, an empty record, or no
    records at all.
    """
    records: list[FastaRecord] = []
    seen_ids: set[str] = set()
    current_id: str | None = None
    current_description = ""
    current_chunks: list[str] = []

    def flush() -> None:
        nonlocal current_id, current_description, current_chunks
        if current_id is None:
            return
        sequence = normalize_sequence("".join(current_chunks), seq_type)
        records.append(
            FastaRecord(id=current_id, description=current_description, sequence=sequence)
        )
        current_id, current_description, current_chunks = None, "", []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            flush()
            header = line[1:].strip()
            parts = header.split(None, 1)
            current_id = parts[0] if parts else ""
            current_description = parts[1] if len(parts) > 1 else ""
            if not current_id:
                raise ValueError("FASTA header is missing an id")
            if current_id in seen_ids:
                raise ValueError(f"duplicate FASTA id: {current_id}")
            seen_ids.add(current_id)
        else:
            if current_id is None:
                raise ValueError("FASTA sequence data appears before any header")
            current_chunks.append(line)

    flush()
    if not records:
        raise ValueError("no FASTA records found")
    return tuple(records)


def read_fasta(path: Path, *, seq_type: SeqType) -> tuple[FastaRecord, ...]:
    return parse_fasta(path.read_text(), seq_type=seq_type)
