"""Parser for raw HMMER ``--domtblout`` output (used by the family differential test).

The in-process family search uses pyhmmer objects directly; this text parser only
exists to cross-check pyhmmer against the raw ``hmmsearch`` binary.
"""

from __future__ import annotations

from veritas.contamination.hits import FamilyAssignment


def parse_domtblout(text: str) -> list[FamilyAssignment]:
    assignments: list[FamilyAssignment] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        # hmmsearch --domtblout: col1=target(sequence) col4=query(HMM/family) col7=full-seq E-value
        assignments.append(
            FamilyAssignment(item_id=parts[0], family=parts[3], e_value=float(parts[6]))
        )
    return assignments
