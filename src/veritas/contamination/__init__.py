"""Contamination detection engine: pluggable detectors over a common interface."""

from __future__ import annotations

from veritas.contamination.base import AlphabetError, ContaminationDetector
from veritas.contamination.compose import combine
from veritas.contamination.family import FamilyDetector
from veritas.contamination.graph import (
    contaminated_eval_ids,
    filter_by_score,
    intersect,
    nearest_score_by_eval,
    union,
)
from veritas.contamination.hits import FamilyAssignment, SequenceHit, StructuralHit
from veritas.contamination.prefilter import candidate_pairs
from veritas.contamination.registry import (
    available_detectors,
    get_detector,
    register_detector,
)
from veritas.contamination.sequence_identity import SequenceIdentityDetector
from veritas.contamination.structural import StructuralDetector

__all__ = [
    "AlphabetError",
    "ContaminationDetector",
    "FamilyAssignment",
    "FamilyDetector",
    "SequenceHit",
    "SequenceIdentityDetector",
    "StructuralDetector",
    "StructuralHit",
    "available_detectors",
    "candidate_pairs",
    "combine",
    "contaminated_eval_ids",
    "filter_by_score",
    "get_detector",
    "intersect",
    "nearest_score_by_eval",
    "register_detector",
    "union",
]
