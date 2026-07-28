"""Immutable, modality-independent contracts for benchmark-integrity audits."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

# Pydantic v2 cannot generate a schema for this recursive alias on every
# supported interpreter. Report values still cross the JSON serialization
# boundary, while this keeps core contracts importable without provider extras.
JsonValue: TypeAlias = Any


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TaskType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    OPEN_ENDED = "open_ended"
    MATH = "math"
    CODE = "code"
    INSTRUCTION = "instruction_following"


class Visibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    TEMPORAL = "temporal"
    DYNAMIC = "dynamic"


class ValidationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    UNCERTAIN = "uncertain"
    NOT_CHECKED = "not_checked"


class FindingStatus(StrEnum):
    COMPLETE = "complete"
    NOT_RUN = "not_run"
    FAILED = "failed"


class EvidenceDirection(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    INCONCLUSIVE = "inconclusive"


class EvidenceStrength(StrEnum):
    DIRECT = "direct"
    STRONG_INDIRECT = "strong_indirect"
    WEAK_INDIRECT = "weak_indirect"
    AGAINST = "against"
    INCONCLUSIVE = "inconclusive"
    UNAVAILABLE = "unavailable"


class Choice(Contract):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class SourceRecord(Contract):
    name: str
    uri: HttpUrl | None = None
    license: str | None = None
    content_hash: str | None = None


class BenchmarkItem(Contract):
    id: str = Field(min_length=1)
    prompt: str | tuple[dict[str, JsonValue], ...]
    expected_output: JsonValue
    task_type: TaskType
    choices: tuple[Choice, ...] | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    source: SourceRecord | None = None
    release_date: datetime | None = None
    family_id: str | None = None
    attachments: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _choice_answer_is_declared(self) -> BenchmarkItem:
        if self.choices and str(self.expected_output) not in {choice.id for choice in self.choices}:
            raise ValueError("multiple-choice expected_output must be a declared choice id")
        return self


class ScoringSpec(Contract):
    kind: str = "exact_match"
    config: dict[str, JsonValue] = Field(default_factory=dict)


class Benchmark(Contract):
    id: str
    version: str
    items: tuple[BenchmarkItem, ...] = Field(min_length=1)
    task_type: TaskType
    visibility: Visibility
    split: str = "evaluation"
    scoring: ScoringSpec = Field(default_factory=ScoringSpec)
    source: SourceRecord | None = None
    canonicalization: dict[str, JsonValue] = Field(default_factory=dict)
    release_date: datetime | None = None

    @model_validator(mode="after")
    def _item_ids_are_unique(self) -> Benchmark:
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("benchmark item ids must be unique")
        if any(item.task_type is not self.task_type for item in self.items):
            raise ValueError("benchmark items must share benchmark task_type")
        return self


class GenerationConfig(Contract):
    temperature: float = Field(default=0.0, ge=0.0)
    max_tokens: int = Field(default=512, gt=0)
    seed: int | None = None
    extra: dict[str, JsonValue] = Field(default_factory=dict)


class ModelCapabilities(Contract):
    token_probabilities: bool = False
    deterministic_seed: bool = False
    tools: bool = False


class ModelTarget(Contract):
    id: str
    adapter: str
    provider: str | None = None
    endpoint: str | None = None
    revision: str | None = None
    open_weight: bool = False
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    system_prompt: str | None = None
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    request_limit: int = Field(default=10_000, gt=0)
    token_limit: int = Field(default=1_000_000, gt=0)
    max_cost_usd: float | None = Field(default=None, ge=0)
    adapter_version: str = "1"


class ModelResponse(Contract):
    item_id: str
    request: dict[str, JsonValue]
    normalized_request: dict[str, JsonValue]
    raw_text: str
    parsed_answer: JsonValue | None = None
    token_logprobs: tuple[float, ...] | None = None
    latency_ms: float | None = None
    token_count: int | None = None
    finish_reason: str | None = None
    attempt: int = 1
    error: str | None = None
    provenance: dict[str, JsonValue] = Field(default_factory=dict)


class Transformation(Contract):
    id: str
    family: str
    parent_item_id: str
    child_item_id: str
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    seed: int
    validation: ValidationStatus = ValidationStatus.NOT_CHECKED
    validation_method: str | None = None
    expected_output: JsonValue
    content_hash: str | None = None


class DetectorFinding(Contract):
    detector_id: str
    detector_version: str
    hypothesis: str
    status: FindingStatus = FindingStatus.COMPLETE
    evidence_type: str
    statistic: float | None = None
    effect_size: float | None = None
    ci: tuple[float, float] | None = None
    p_value: float | None = None
    corrected_p_value: float | None = None
    direction: EvidenceDirection = EvidenceDirection.INCONCLUSIVE
    strength: EvidenceStrength = EvidenceStrength.INCONCLUSIVE
    assumptions: tuple[str, ...] = ()
    alternative_explanations: tuple[str, ...] = ()
    calibration: str = "not_calibrated"
    item_ids: tuple[str, ...] = ()
    details: dict[str, JsonValue] = Field(default_factory=dict)


class ScoreSummary(Contract):
    reported_score: float | None = None
    canonical_reproduced_score: float | None = None
    robust_score: float | None = None
    fresh_score: float | None = None
    robustness_gap: float | None = None
    fresh_generalization_gap: float | None = None
    ci: tuple[float, float] | None = None


class EvidenceMatrixRow(Contract):
    hypothesis: str
    supporting: tuple[str, ...] = ()
    contradicting: tuple[str, ...] = ()
    unavailable: tuple[str, ...] = ()
    confidence: EvidenceStrength = EvidenceStrength.INCONCLUSIVE
    assumptions: tuple[str, ...] = ()


class AuditProvenance(Contract):
    benchmark_hash: str
    audit_spec_hash: str
    model: ModelTarget
    seeds: dict[str, int] = Field(default_factory=dict)
    cache_state: str = "disabled"
    privacy_warnings: tuple[str, ...] = ()
    external_transfer_acknowledged: bool = False
    package_version: str = "0.2.0"


class AuditReport(Contract):
    schema_version: Literal["2.0"] = "2.0"
    audit_hash: str
    benchmark: Benchmark
    score: ScoreSummary
    findings: tuple[DetectorFinding, ...]
    evidence_matrix: tuple[EvidenceMatrixRow, ...]
    transformations: tuple[Transformation, ...] = ()
    responses: tuple[ModelResponse, ...] = ()
    limitations: tuple[str, ...] = ()
    provenance: AuditProvenance


class DetectorSpec(Contract):
    type: str
    enabled: bool = True
    config: dict[str, JsonValue] = Field(default_factory=dict)


class TransformationSpec(Contract):
    type: str
    variants_per_item: int = Field(default=1, gt=0)
    validator: str | None = None


class AuditSpec(Contract):
    schema_version: Literal["2.0"] = "2.0"
    benchmark: dict[str, JsonValue]
    model: ModelTarget
    transformations: tuple[TransformationSpec, ...] = ()
    detectors: tuple[DetectorSpec, ...] = ()
    runtime: dict[str, JsonValue] = Field(default_factory=dict)
    report: dict[str, JsonValue] = Field(default_factory=dict)
