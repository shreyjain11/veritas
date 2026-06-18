"""The common contamination-detector interface (CLAUDE.md first principle #5)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import ClassVar

from veritas.contracts import (
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    ReferenceItem,
    SeqType,
)


class AlphabetError(ValueError):
    """Raised when a detector is applied to a sequence type it does not support."""


class ContaminationDetector(ABC):
    kind: ClassVar[DetectorKind]
    supported_alphabets: ClassVar[frozenset[SeqType]]
    detector_id: str
    #: Absolute path of the resolved backend binary, or None for in-process / unresolved
    #: detectors. Recorded in the provenance manifest by the orchestrator.
    binary_path: str | None = None

    def _check_alphabets(self, *item_groups: Sequence[EvalItem] | Sequence[ReferenceItem]) -> None:
        for group in item_groups:
            for item in group:
                if item.seq_type not in self.supported_alphabets:
                    raise AlphabetError(
                        f"detector {self.detector_id!r} ({self.kind}) does not support "
                        f"{item.seq_type} sequences"
                    )

    @abstractmethod
    def detect(
        self,
        eval_items: Sequence[EvalItem],
        reference_items: Sequence[ReferenceItem],
        config: DetectorConfig,
    ) -> ContaminationGraph: ...
