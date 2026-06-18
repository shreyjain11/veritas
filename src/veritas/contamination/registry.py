"""Registry mapping detector names to detector instances (kept model-agnostic)."""

from __future__ import annotations

from collections.abc import Callable

from veritas.contamination.backends.diamond import DiamondSearch
from veritas.contamination.backends.foldseek import FoldseekSearch
from veritas.contamination.backends.mmseqs import MmseqsSearch
from veritas.contamination.backends.pyhmmer_search import PyhmmerSearch
from veritas.contamination.base import ContaminationDetector
from veritas.contamination.family import FamilyDetector
from veritas.contamination.sequence_identity import SequenceIdentityDetector
from veritas.contamination.structural import StructuralDetector

_REGISTRY: dict[str, Callable[[], ContaminationDetector]] = {
    "mmseqs": lambda: SequenceIdentityDetector(search=MmseqsSearch(), detector_id="mmseqs"),
    "diamond": lambda: SequenceIdentityDetector(search=DiamondSearch(), detector_id="diamond"),
    "pyhmmer": lambda: FamilyDetector(search=PyhmmerSearch(), detector_id="pyhmmer"),
    "foldseek": lambda: StructuralDetector(search=FoldseekSearch(), detector_id="foldseek"),
}


def register_detector(name: str, factory: Callable[[], ContaminationDetector]) -> None:
    _REGISTRY[name] = factory


def available_detectors() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def get_detector(name: str) -> ContaminationDetector:
    if name not in _REGISTRY:
        raise KeyError(f"unknown detector: {name!r}; available: {available_detectors()}")
    return _REGISTRY[name]()
