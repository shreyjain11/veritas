"""Shared application service for the v2 CLI and MCP boundaries."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from veritas.benchmark_integrity.adapters import (
    HuggingFaceLocalAdapter,
    JsonlBenchmarkAdapter,
    ModelAdapter,
    OpenAICompatibleAdapter,
    ReplayAdapter,
)
from veritas.benchmark_integrity.cache import CachedAdapter
from veritas.benchmark_integrity.catalog import CATALOG, CatalogBenchmarkAdapter
from veritas.benchmark_integrity.contracts import (
    AuditProvenance,
    AuditReport,
    AuditSpec,
    Benchmark,
    DetectorFinding,
    EvidenceDirection,
    EvidenceMatrixRow,
    EvidenceStrength,
    FindingStatus,
    ModelResponse,
    ScoreSummary,
    Visibility,
)
from veritas.benchmark_integrity.statistics import (
    mcnemar_exact,
    paired_bootstrap_gap,
    paired_permutation_p_value,
)
from veritas.benchmark_integrity.transforms import DerivedItem, generate

_DETECTOR_HYPOTHESES = {
    "guided_completion": "semantic or benchmark-specific continuation exposure",
    "fresh_set": "fresh-set generalization",
    "temporal": "temporal generalization",
    "error_reproduction": "reproduction of documented benchmark artifacts",
    "cross_model": "cross-model anomaly requiring comparative controls",
    "evaluator_exploitation": "evaluator or grader exploitation",
    "consistency": "repeated-sampling consistency",
}


def load_spec(path: Path) -> AuditSpec:
    """Load JSON, or YAML when PyYAML is installed, without a hard YAML dependency."""
    raw = path.read_text(encoding="utf-8")
    try:
        data: object = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ValueError(
                "YAML audit specs require the 'yaml' extra; use JSON or install PyYAML"
            ) from exc
        data = yaml.safe_load(raw)
    return AuditSpec.model_validate(data)


def inspect_audit(spec: AuditSpec) -> dict[str, Any]:
    benchmark_cfg = spec.benchmark
    count = _item_count(benchmark_cfg)
    variants = sum(transform.variants_per_item for transform in spec.transformations)
    requests = count * (1 + variants)
    private = str(benchmark_cfg.get("visibility", "public")) == Visibility.PRIVATE.value
    external = spec.model.adapter not in {"replay", "subprocess", "huggingface_local"}
    warnings: list[str] = []
    if private and external:
        warnings.append(
            "Private benchmark content will be sent to an external configured endpoint."
        )
    probability_available = spec.model.capabilities.token_probabilities or spec.model.adapter in {
        "replay",
        "huggingface_local",
    }
    unavailable = [
        d.type for d in spec.detectors if d.type == "probability" and not probability_available
    ]
    return {
        "estimated_requests": requests,
        "estimated_max_tokens": requests * spec.model.generation.max_tokens,
        "privacy_warnings": warnings,
        "unavailable_detectors": unavailable,
        "requires_external_transfer_acknowledgement": bool(warnings),
        "model_capabilities": {
            "token_probabilities": probability_available,
            "deterministic_seed": spec.model.capabilities.deterministic_seed
            or spec.model.adapter in {"replay", "huggingface_local"},
        },
    }


def audit(
    spec: AuditSpec,
    *,
    adapter: ModelAdapter | None = None,
    acknowledge_external_transfer: bool = False,
) -> AuditReport:
    benchmark = load_benchmark(spec.benchmark)
    check = inspect_audit(
        spec.model_copy(
            update={"benchmark": {**spec.benchmark, "item_count": len(benchmark.items)}}
        )
    )
    if check["requires_external_transfer_acknowledgement"] and not acknowledge_external_transfer:
        raise PermissionError(
            "private benchmark external transfer requires explicit acknowledgement"
        )
    estimated_requests = len(benchmark.items) * (
        1 + sum(value.variants_per_item for value in spec.transformations)
    )
    if estimated_requests > spec.model.request_limit:
        raise ValueError(
            f"audit requires {estimated_requests} requests, exceeding request_limit "
            f"{spec.model.request_limit}"
        )
    estimated_tokens = estimated_requests * spec.model.generation.max_tokens
    if estimated_tokens > spec.model.token_limit:
        raise ValueError(
            f"audit may generate {estimated_tokens} tokens, exceeding token_limit "
            f"{spec.model.token_limit}"
        )
    model_adapter = adapter or _adapter_for(spec, benchmark)
    cache_dir = spec.runtime.get("cache_dir")
    if cache_dir:
        model_adapter = CachedAdapter(model_adapter, spec.model, Path(str(cache_dir)))
    canonical = tuple(model_adapter.generate(benchmark.items, spec.model.generation))
    transforms = tuple(
        derived
        for transform in spec.transformations
        for derived in generate(
            benchmark.items,
            transform.type,
            transform.variants_per_item,
            int(spec.runtime.get("seed", 42)),
        )
    )
    transformed_responses = (
        tuple(
            model_adapter.generate([derived.item for derived in transforms], spec.model.generation)
        )
        if transforms
        else ()
    )
    findings = _findings(
        spec,
        benchmark,
        canonical,
        transforms,
        transformed_responses,
        token_probabilities=model_adapter.capabilities().token_probabilities,
    )
    score = _scores(benchmark, canonical, transforms, transformed_responses)
    benchmark_hash = _hash(benchmark.model_dump(mode="json"))
    spec_hash = _hash(spec.model_dump(mode="json"))
    provenance = AuditProvenance(
        benchmark_hash=benchmark_hash,
        audit_spec_hash=spec_hash,
        model=spec.model,
        seeds={"runtime": int(spec.runtime.get("seed", 42))},
        cache_state="enabled" if cache_dir else "disabled",
        privacy_warnings=tuple(check["privacy_warnings"]),
        external_transfer_acknowledged=acknowledge_external_transfer,
    )
    matrix = _matrix(findings)
    payload = {
        "benchmark": benchmark_hash,
        "spec": spec_hash,
        "responses": [r.model_dump(mode="json") for r in canonical],
        "findings": [f.model_dump(mode="json") for f in findings],
    }
    return AuditReport(
        audit_hash=_hash(payload),
        benchmark=benchmark,
        score=score,
        findings=tuple(findings),
        evidence_matrix=matrix,
        transformations=tuple(derived.transformation for derived in transforms),
        responses=canonical + transformed_responses,
        limitations=(
            "Behavioral evidence cannot establish a closed model's training membership.",
            "Generated variants are reported separately by validation status.",
        ),
        provenance=provenance,
    )


def _adapter_for(spec: AuditSpec, benchmark: Benchmark) -> ModelAdapter:
    if spec.model.adapter == "replay":
        values = spec.model.generation.extra.get("responses", {})
        if not isinstance(values, dict):
            raise ValueError("replay generation.extra.responses must be an object")
        return ReplayAdapter(values)
    if spec.model.adapter == "huggingface_local":
        return HuggingFaceLocalAdapter(spec.model)
    if spec.model.adapter in {"openai_compatible", "vllm"}:
        return OpenAICompatibleAdapter(
            spec.model,
            str(spec.model.generation.extra.get("api_key_env", "MODEL_API_KEY")),
            require_api_key=spec.model.adapter != "vllm",
        )
    raise ValueError(f"unsupported model adapter {spec.model.adapter!r}")


def load_benchmark(config: dict[str, Any]) -> Benchmark:
    """Resolve a benchmark adapter without importing optional dataset SDKs in core."""
    adapter = str(config.get("adapter", "jsonl"))
    if adapter == "jsonl":
        return JsonlBenchmarkAdapter().load(config)
    if adapter == "catalog":
        return CatalogBenchmarkAdapter().load(config)
    raise ValueError(f"unsupported benchmark adapter {adapter!r}")


def _item_count(config: dict[str, Any]) -> int:
    declared = config.get("item_count")
    if declared is not None:
        return int(declared)
    if str(config.get("adapter", "jsonl")) == "catalog":
        limit = config.get("limit")
        if limit is not None:
            return int(limit)
        entry = CATALOG.get(str(config.get("name", "")))
        return entry.approximate_items or 0 if entry else 0
    path = config.get("path")
    if path is None:
        return 0
    return sum(
        1 for line in Path(str(path)).read_text(encoding="utf-8").splitlines() if line.strip()
    )


def _correct(item_id: str, benchmark: Benchmark, responses: Sequence[ModelResponse]) -> bool:
    expected = next(
        item.expected_output for item in benchmark.items if item.id == item_id.split("::")[0]
    )
    return _response_correct(item_id, expected, responses)


def _response_correct(item_id: str, expected: object, responses: Sequence[ModelResponse]) -> bool:
    response = next((r for r in responses if r.item_id == item_id), None)
    return response is not None and str(response.parsed_answer).strip() == str(expected).strip()


def _scores(
    benchmark: Benchmark,
    canonical: Sequence[ModelResponse],
    transforms: Sequence[DerivedItem],
    transformed: Sequence[ModelResponse],
) -> ScoreSummary:
    if benchmark.scoring.kind.startswith("external_"):
        return ScoreSummary()
    canonical_score = sum(
        _correct(item.id, benchmark, canonical) for item in benchmark.items
    ) / len(benchmark.items)
    valid = [item for item in transforms if item.transformation.validation.value == "valid"]
    robust = None
    confidence_interval = None
    if valid:
        transformed_by_parent: dict[str, list[float]] = {}
        for derived in valid:
            transformed_by_parent.setdefault(derived.transformation.parent_item_id, []).append(
                float(
                    _response_correct(
                        derived.item.id,
                        derived.item.expected_output,
                        transformed,
                    )
                )
            )
        parents = [item.id for item in benchmark.items if item.id in transformed_by_parent]
        canonical_values = [float(_correct(item_id, benchmark, canonical)) for item_id in parents]
        transformed_values = [
            sum(transformed_by_parent[item_id]) / len(transformed_by_parent[item_id])
            for item_id in parents
        ]
        robust = sum(transformed_values) / len(transformed_values)
        confidence_interval = paired_bootstrap_gap(canonical_values, transformed_values)
    return ScoreSummary(
        canonical_reproduced_score=canonical_score,
        robust_score=robust,
        robustness_gap=(canonical_score - robust) if robust is not None else None,
        ci=confidence_interval,
    )


def _findings(
    spec: AuditSpec,
    benchmark: Benchmark,
    canonical: Sequence[ModelResponse],
    transforms: Sequence[DerivedItem],
    transformed: Sequence[ModelResponse],
    *,
    token_probabilities: bool,
) -> list[DetectorFinding]:
    findings: list[DetectorFinding] = []
    names = {detector.type for detector in spec.detectors if detector.enabled}
    if "perturbation" in names or transforms:
        score = _scores(benchmark, canonical, transforms, transformed)
        gap = score.robustness_gap
        direction = (
            EvidenceDirection.SUPPORTS
            if gap is not None and gap > 0
            else EvidenceDirection.INCONCLUSIVE
        )
    for detector_id, families, hypothesis in (
        (
            "option_order",
            {"choice_permutation", "choice_label_remap"},
            "answer-position or label-token dependence",
        ),
        (
            "template_dependence",
            {"formatting"},
            "benchmark-template or prompt-protocol dependence",
        ),
    ):
        if detector_id in names:
            selected = [value for value in transforms if value.transformation.family in families]
            if selected:
                family_score = _scores(benchmark, canonical, selected, transformed)
                family_details = _paired_details(benchmark, canonical, selected, transformed)
                family_gap = family_score.robustness_gap
                findings.append(
                    DetectorFinding(
                        detector_id=detector_id,
                        detector_version="1",
                        hypothesis=hypothesis,
                        evidence_type="paired transformation-family accuracy",
                        statistic=family_gap,
                        effect_size=family_gap,
                        ci=family_score.ci,
                        p_value=_float_detail(family_details, "permutation_p_value"),
                        direction=EvidenceDirection.SUPPORTS
                        if family_gap is not None and family_gap > 0
                        else EvidenceDirection.INCONCLUSIVE,
                        strength=EvidenceStrength.WEAK_INDIRECT
                        if family_gap is not None and family_gap > 0
                        else EvidenceStrength.INCONCLUSIVE,
                        assumptions=("The selected deterministic variants preserve task content.",),
                        alternative_explanations=(
                            "parser sensitivity",
                            "ordinary distribution shift",
                        ),
                        details=family_details,
                    )
                )
            else:
                findings.append(
                    DetectorFinding(
                        detector_id=detector_id,
                        detector_version="1",
                        hypothesis=hypothesis,
                        status=FindingStatus.NOT_RUN,
                        evidence_type="required transformation family unavailable",
                        strength=EvidenceStrength.UNAVAILABLE,
                    )
                )
        paired_details = _paired_details(benchmark, canonical, transforms, transformed)
        findings.append(
            DetectorFinding(
                detector_id="perturbation",
                detector_version="1",
                hypothesis="benchmark-template overfitting or surface-form dependence",
                evidence_type="paired validated transformation accuracy",
                statistic=gap,
                effect_size=gap,
                ci=score.ci,
                p_value=paired_details.get("permutation_p_value"),
                direction=direction,
                strength=EvidenceStrength.WEAK_INDIRECT
                if direction is EvidenceDirection.SUPPORTS
                else EvidenceStrength.INCONCLUSIVE,
                assumptions=("Validated transformations preserve intended task difficulty.",),
                alternative_explanations=(
                    "ordinary distribution shift",
                    "parser sensitivity",
                    "stochastic variance",
                ),
                details={
                    "canonical_score": score.canonical_reproduced_score,
                    "robust_score": score.robust_score,
                    **paired_details,
                },
            )
        )
    if "probability" in names and not token_probabilities:
        findings.append(
            DetectorFinding(
                detector_id="probability",
                detector_version="1",
                hypothesis="exposure evidence from token probabilities",
                status=FindingStatus.NOT_RUN,
                evidence_type="token likelihood",
                strength=EvidenceStrength.UNAVAILABLE,
                assumptions=("Token probabilities are available.",),
                alternative_explanations=("API does not expose log probabilities.",),
            )
        )
    elif "probability" in names:
        sequences = [response.token_logprobs for response in canonical if response.token_logprobs]
        if not sequences:
            findings.append(
                DetectorFinding(
                    detector_id="probability",
                    detector_version="1",
                    hypothesis="exposure evidence from token probabilities",
                    status=FindingStatus.NOT_RUN,
                    evidence_type="token likelihood",
                    strength=EvidenceStrength.UNAVAILABLE,
                    assumptions=("Responses contain generated-token log probabilities.",),
                    alternative_explanations=(
                        "Adapter declared support but returned no log probabilities.",
                    ),
                )
            )
        else:
            nll = [-sum(values) / len(values) for values in sequences]
            findings.append(
                DetectorFinding(
                    detector_id="probability",
                    detector_version="1",
                    hypothesis="exposure evidence from token probabilities",
                    evidence_type="mean generated-token negative log likelihood",
                    statistic=sum(nll) / len(nll),
                    direction=EvidenceDirection.INCONCLUSIVE,
                    strength=EvidenceStrength.INCONCLUSIVE,
                    calibration="uncalibrated_without_matched_member/non-member_controls",
                    assumptions=("Generated-token likelihood is comparable across items.",),
                    alternative_explanations=(
                        "domain familiarity",
                        "model confidence",
                        "tokenization",
                    ),
                    details={"n_items_with_logprobs": len(nll)},
                )
            )
    if "exact_match" in names:
        refs = (
            [str(v) for v in spec.runtime.get("reference_texts", [])]
            if isinstance(spec.runtime.get("reference_texts", []), list)
            else []
        )
        matched = tuple(
            item.id
            for item in benchmark.items
            if isinstance(item.prompt, str) and item.prompt in refs
        )
        findings.append(
            DetectorFinding(
                detector_id="exact_match",
                detector_version="1",
                hypothesis="exact public-reference overlap",
                evidence_type="verified lexical prompt overlap",
                statistic=float(len(matched)),
                effect_size=len(matched) / len(benchmark.items),
                direction=EvidenceDirection.SUPPORTS if matched else EvidenceDirection.INCONCLUSIVE,
                strength=EvidenceStrength.DIRECT if matched else EvidenceStrength.INCONCLUSIVE,
                item_ids=matched,
                assumptions=(
                    "Reference corpus is relevant and complete enough for this comparison.",
                ),
                alternative_explanations=(
                    "Publication overlap does not prove model training exposure.",
                ),
            )
        )
    for detector_id, hypothesis in _DETECTOR_HYPOTHESES.items():
        if detector_id in names:
            findings.append(
                DetectorFinding(
                    detector_id=detector_id,
                    detector_version="1",
                    hypothesis=hypothesis,
                    status=FindingStatus.NOT_RUN,
                    evidence_type="requirements not supplied in initial adapter run",
                    strength=EvidenceStrength.UNAVAILABLE,
                    assumptions=("Required matched controls and detector inputs are configured.",),
                    alternative_explanations=(
                        "This audit configuration did not provide the required data or access.",
                    ),
                )
            )
    return findings


def _paired_details(
    benchmark: Benchmark,
    canonical: Sequence[ModelResponse],
    transforms: Sequence[DerivedItem],
    transformed: Sequence[ModelResponse],
) -> dict[str, Any]:
    valid = [value for value in transforms if value.transformation.validation.value == "valid"]
    by_parent: dict[str, list[bool]] = {}
    for derived in valid:
        by_parent.setdefault(derived.transformation.parent_item_id, []).append(
            _response_correct(derived.item.id, derived.item.expected_output, transformed)
        )
    parents = [item.id for item in benchmark.items if item.id in by_parent]
    if not parents:
        return {}
    left = [_correct(parent, benchmark, canonical) for parent in parents]
    right_score = [sum(by_parent[parent]) / len(by_parent[parent]) for parent in parents]
    right_binary = [value >= 0.5 for value in right_score]
    return {
        "parent_item_count": len(parents),
        "permutation_p_value": paired_permutation_p_value(
            [float(value) for value in left], right_score
        ),
        "mcnemar": mcnemar_exact(left, right_binary),
    }


def _float_detail(details: dict[str, Any], key: str) -> float | None:
    value = details.get(key)
    return float(value) if isinstance(value, int | float) else None


def _matrix(findings: Sequence[DetectorFinding]) -> tuple[EvidenceMatrixRow, ...]:
    rows: list[EvidenceMatrixRow] = []
    for hypothesis in (
        "exact exposure",
        "semantic exposure",
        "template overfitting",
        "protocol dependence",
        "answer-position dependence",
        "evaluator exploitation",
        "fresh-set generalization",
        "temporal generalization",
        "ordinary distribution shift",
    ):
        related = [finding for finding in findings if hypothesis.split()[0] in finding.hypothesis]
        rows.append(
            EvidenceMatrixRow(
                hypothesis=hypothesis,
                supporting=tuple(
                    f.detector_id for f in related if f.direction is EvidenceDirection.SUPPORTS
                ),
                unavailable=tuple(
                    f.detector_id for f in related if f.status is FindingStatus.NOT_RUN
                ),
                confidence=max(
                    (f.strength for f in related),
                    default=EvidenceStrength.UNAVAILABLE,
                    key=lambda strength: list(EvidenceStrength).index(strength),
                ),
            )
        )
    return tuple(rows)


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
