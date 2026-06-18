"""Sequence alphabets and normalization shared by contracts and IO loaders.

Sequences are normalized to uppercase and validated against the IUPAC alphabet
for their declared :class:`SeqType` (docs/PLAN.md decision #22).
"""

from __future__ import annotations

from pydantic import ValidationInfo

from veritas.contracts.enums import SeqType

#: 20 standard amino acids plus ambiguity/special codes (X B Z J U O).
PROTEIN_ALPHABET = frozenset("ACDEFGHIKLMNPQRSTVWYXBZJUO")
#: IUPAC nucleotide codes (DNA + RNA + ambiguity).
NUCLEOTIDE_ALPHABET = frozenset("ACGTUNRYSWKMBDHV")


def alphabet_for(seq_type: SeqType) -> frozenset[str]:
    return PROTEIN_ALPHABET if seq_type is SeqType.PROTEIN else NUCLEOTIDE_ALPHABET


def normalize_sequence(sequence: str, seq_type: SeqType) -> str:
    """Uppercase, strip, and validate a sequence against its alphabet.

    Raises :class:`ValueError` if the sequence is empty or contains characters
    outside the alphabet for ``seq_type``.
    """
    normalized = sequence.strip().upper()
    if not normalized:
        raise ValueError("sequence must be non-empty")
    invalid = sorted(set(normalized) - alphabet_for(seq_type))
    if invalid:
        raise ValueError(
            f"sequence contains characters outside the {seq_type.value} alphabet: {invalid}"
        )
    return normalized


def normalize_sequence_field(value: str, info: ValidationInfo) -> str:
    """pydantic field-validator helper: normalize ``sequence`` using the model's ``seq_type``.

    If ``seq_type`` is absent or invalid, the value is returned unchanged so that
    the ``seq_type`` validation error surfaces on its own.
    """
    seq_type = info.data.get("seq_type")
    if not isinstance(seq_type, SeqType):
        return value
    return normalize_sequence(value, seq_type)
