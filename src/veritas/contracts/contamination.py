"""Contamination graph schema (the engine that builds it lives in Phase 2)."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from veritas.contracts.base import FrozenModel
from veritas.contracts.enums import DetectorKind


class ContaminationEdge(FrozenModel):
    eval_id: str
    ref_id: str
    score: float = Field(ge=0.0)
    kind: DetectorKind
    detector_id: str
    details: dict[str, Any] = Field(default_factory=dict)


class ContaminationGraph(FrozenModel):
    edges: tuple[ContaminationEdge, ...] = ()
