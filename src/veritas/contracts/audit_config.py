"""AuditConfig and per-detector configuration."""

from __future__ import annotations

from typing import Any, Self

from pydantic import Field, model_validator

from veritas.contracts.base import FrozenModel
from veritas.contracts.enums import CombinePolicy, DeLeakPolicy, DetectorKind


class DetectorConfig(FrozenModel):
    kind: DetectorKind
    name: str
    identity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    coverage_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    e_value_threshold: float | None = Field(default=None, gt=0.0)
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    extra_params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _require_kind_thresholds(self) -> Self:
        if self.kind is DetectorKind.SEQUENCE and self.identity_threshold is None:
            raise ValueError("a sequence detector requires identity_threshold")
        if self.kind is DetectorKind.FAMILY and self.e_value_threshold is None:
            raise ValueError("a family detector requires e_value_threshold")
        if self.kind is DetectorKind.STRUCTURE and self.score_threshold is None:
            raise ValueError("a structure detector requires score_threshold")
        return self


class AuditConfig(FrozenModel):
    detectors: tuple[DetectorConfig, ...] = Field(min_length=1)
    seed: int
    combine_policy: CombinePolicy = CombinePolicy.UNION
    deleak_policy: DeLeakPolicy = DeLeakPolicy.DROP
    bootstrap_n: int = Field(default=1000, gt=0)
    ci_level: float = Field(default=0.95, gt=0.0, lt=1.0)
    stratify_axes: tuple[str, ...] = ()
    # Declared pinned tool versions (from environment.yml), keyed by tool name. The
    # orchestrator compares these to the runtime-captured versions; it never derives
    # the pin by probing the binary that is about to run (req C: a drifted binary
    # must surface as a mismatch, not be silently accepted).
    pinned_versions: dict[str, str] = Field(default_factory=dict)
