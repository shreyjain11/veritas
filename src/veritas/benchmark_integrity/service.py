"""Shared application service for the v2 CLI and MCP boundaries."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from veritas import __version__
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
    DetectorSpec,
    EvidenceDirection,
    EvidenceMatrixRow,
    EvidenceStrength,
    FindingStatus,
    ModelResponse,
    ScoreSummary,
    ValidationStatus,
    Visibility,
)
from veritas.benchmark_integrity.hashing import report_hash
from veritas.benchmark_integrity.prompting import normalize_answer, prompt_text
from veritas.benchmark_integrity.statistics import (
    benjamini_hochberg,
    mcnemar_exact,
    paired_bootstrap_gap,
    paired_permutation_p_value,
)
from veritas.benchmark_integrity.transforms import TRANSFORMS, DerivedItem, generate

# Detectors that compare canonical vs. transformed accuracy on the same parent items.
# ``None`` selects every validated transformation family.
_PAIRED_DETECTORS: dict[str, tuple[frozenset[str] | None, str]] = {
    "perturbation": (None, "benchmark-template overfitting or surface-form dependence"),
    "option_order": (
        frozenset({"choice_permutation", "choice_label_remap"}),
        "answer-position or label-token dependence",
    ),
    "template_dependence": (
        frozenset({"formatting"}),
        "benchmark-template or prompt-protocol dependence",
    ),
}
_DETECTOR_HYPOTHESES = {
    "guided_completion": "semantic or benchmark-specific continuation exposure",
    "fresh_set": "fresh-set generalization",
    "temporal": "temporal generalization",
    "error_reproduction": "reproduction of documented benchmark artifacts",
    "cross_model": "cross-model anomaly requiring comparative controls",
    "evaluator_exploitation": "evaluator or grader exploitation",
    "consistency": "repeated-sampling consistency",
}
DETECTORS: tuple[str, ...] = (
    "exact_match",
    "perturbation",
    "probability",
    "option_order",
    "template_dependence",
    *_DETECTOR_HYPOTHESES,
)
MODEL_ADAPTERS: tuple[str, ...] = ("replay", "openai_compatible", "vllm", "huggingface_local")
_LOCAL_ADAPTERS = frozenset({"replay", "subprocess", "huggingface_local"})

# Which detectors bear on each hypothesis in the evidence matrix.
_MATRIX: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("exact exposure", ("exact_match", "probability")),
    ("semantic exposure", ("guided_completion",)),
    ("template overfitting", ("perturbation", "template_dependence")),
    ("protocol dependence", ("template_dependence", "perturbation")),
    ("answer-position dependence", ("option_order",)),
    ("evaluator exploitation", ("evaluator_exploitation",)),
    ("fresh-set generalization", ("fresh_set",)),
    ("temporal generalization", ("temporal",)),
    ("ordinary distribution shift", ("fresh_set", "temporal")),
)
_STRENGTH_ORDER = list(EvidenceStrength)

# Decision rule defaults for paired detectors (overridable per detector ``config``).
DEFAULT_ALPHA = 0.05
DEFAULT_EQUIVALENCE_MARGIN = 0.05
DEFAULT_MIN_PARENT_ITEMS = 10


def load_spec(path: Path) -> AuditSpec:
    """Load JSON, or YAML when PyYAML is installed, without a hard YAML dependency.

    A relative ``benchmark.path`` that does not exist from the working directory is
    resolved against the spec file's own directory.
    """
    raw = path.read_text(encoding="utf-8")
    try:
        data: object = json.loads(raw)
    except json.JSONDecodeError as json_error:
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ValueError(
                f"{path} is not valid JSON ({json_error.msg} at line {json_error.lineno}); "
                "YAML audit specs require the 'yaml' extra"
            ) from exc
        data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: an audit spec must be a JSON or YAML object")
    benchmark = data.get("benchmark")
    if isinstance(benchmark, dict) and isinstance(benchmark.get("path"), str):
        candidate = Path(benchmark["path"])
        beside_spec = path.parent / candidate
        if not candidate.is_absolute() and not candidate.exists() and beside_spec.exists():
            data = {**data, "benchmark": {**benchmark, "path": str(beside_spec)}}
    try:
        return AuditSpec.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or 'spec'}: {error['msg']}"
            for error in exc.errors()[:3]
        )
        raise ValueError(f"invalid audit spec {path}: {problems}") from exc


def validate_spec(spec: AuditSpec) -> None:
    """Reject unknown transformation or detector names before any work or spend."""
    problems: list[str] = []
    unknown_transforms = sorted({value.type for value in spec.transformations} - set(TRANSFORMS))
    if unknown_transforms:
        problems.append(
            f"unknown transformation(s) {', '.join(unknown_transforms)}; "
            f"available: {', '.join(sorted(TRANSFORMS))}"
        )
    unknown_detectors = sorted({value.type for value in spec.detectors} - set(DETECTORS))
    if unknown_detectors:
        problems.append(
            f"unknown detector(s) {', '.join(unknown_detectors)}; "
            f"available: {', '.join(sorted(DETECTORS))}"
        )
    if problems:
        raise ValueError("; ".join(problems))


def inspect_audit(spec: AuditSpec) -> dict[str, Any]:
    validate_spec(spec)
    benchmark_cfg = spec.benchmark
    count = _item_count(benchmark_cfg)
    variants = sum(transform.variants_per_item for transform in spec.transformations)
    requests = count * (1 + variants)
    private = str(benchmark_cfg.get("visibility", "public")) == Visibility.PRIVATE.value
    external = spec.model.adapter not in _LOCAL_ADAPTERS
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
        "item_count": count,
        "estimated_requests": requests,
        "estimated_max_tokens": requests * spec.model.generation.max_tokens,
        "request_limit": spec.model.request_limit,
        "token_limit": spec.model.token_limit,
        "within_limits": requests <= spec.model.request_limit
        and requests * spec.model.generation.max_tokens <= spec.model.token_limit,
        "privacy_warnings": warnings,
        "unavailable_detectors": unavailable,
        "requires_external_transfer_acknowledgement": bool(warnings),
        "model_capabilities": {
            "token_probabilities": probability_available,
            "deterministic_seed": spec.model.capabilities.deterministic_seed
            or spec.model.adapter in {"replay", "huggingface_local"},
        },
        "notes": [
            "estimated_requests is an upper bound: inapplicable or duplicate variants are skipped."
        ],
    }


def audit(
    spec: AuditSpec,
    *,
    adapter: ModelAdapter | None = None,
    acknowledge_external_transfer: bool = False,
) -> AuditReport:
    validate_spec(spec)
    benchmark = load_benchmark(spec.benchmark)
    check = inspect_audit(
        spec.model_copy(
            update={"benchmark": {**spec.benchmark, "item_count": len(benchmark.items)}}
        )
    )
    if check["requires_external_transfer_acknowledgement"] and not acknowledge_external_transfer:
        raise PermissionError(
            "private benchmark external transfer requires explicit acknowledgement "
            "(--acknowledge-external-transfer)"
        )
    seed = _seed(spec)
    derived = tuple(
        value
        for transform in spec.transformations
        for value in generate(benchmark.items, transform.type, transform.variants_per_item, seed)
    )
    requests = len(benchmark.items) + len(derived)
    if requests > spec.model.request_limit:
        raise ValueError(
            f"audit requires {requests} requests, exceeding request_limit "
            f"{spec.model.request_limit}"
        )
    estimated_tokens = requests * spec.model.generation.max_tokens
    if estimated_tokens > spec.model.token_limit:
        raise ValueError(
            f"audit may generate {estimated_tokens} tokens, exceeding token_limit "
            f"{spec.model.token_limit}"
        )
    model_adapter = adapter or _adapter_for(spec)
    cache_dir = spec.runtime.get("cache_dir")
    if cache_dir:
        model_adapter = CachedAdapter(model_adapter, spec.model, Path(str(cache_dir)))
    canonical = tuple(model_adapter.generate(benchmark.items, spec.model.generation))
    transformed = (
        tuple(model_adapter.generate([value.item for value in derived], spec.model.generation))
        if derived
        else ()
    )
    analysis = _Analysis(spec, benchmark, canonical, derived, transformed, seed)
    findings = analysis.findings(
        token_probabilities=model_adapter.capabilities().token_probabilities
    )
    provenance = AuditProvenance(
        benchmark_hash=report_hash(benchmark.model_dump(mode="json")),
        audit_spec_hash=report_hash(spec.model_dump(mode="json")),
        model=spec.model,
        seeds={"runtime": seed},
        cache_state="enabled" if cache_dir else "disabled",
        privacy_warnings=tuple(check["privacy_warnings"]),
        external_transfer_acknowledged=acknowledge_external_transfer,
        package_version=__version__,
    )
    report = AuditReport(
        audit_hash="",
        benchmark=benchmark,
        score=analysis.score(),
        findings=tuple(findings),
        evidence_matrix=_matrix(findings),
        transformations=tuple(value.transformation for value in derived),
        responses=canonical + transformed,
        limitations=analysis.limitations(),
        provenance=provenance,
    )
    return report.model_copy(update={"audit_hash": report_hash(report.model_dump(mode="json"))})


def _seed(spec: AuditSpec) -> int:
    value = spec.runtime.get("seed", 42)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"runtime.seed must be an integer, got {value!r}") from exc


def _adapter_for(spec: AuditSpec) -> ModelAdapter:
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
    raise ValueError(
        f"unsupported model adapter {spec.model.adapter!r}; available: {', '.join(MODEL_ADAPTERS)}"
    )


def load_benchmark(config: dict[str, Any]) -> Benchmark:
    """Resolve a benchmark adapter without importing optional dataset SDKs in core."""
    adapter = str(config.get("adapter", "jsonl"))
    if adapter == "jsonl":
        return JsonlBenchmarkAdapter().load(config)
    if adapter == "catalog":
        return CatalogBenchmarkAdapter().load(config)
    raise ValueError(f"unsupported benchmark adapter {adapter!r}; available: catalog, jsonl")


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
    if path is None or not Path(str(path)).is_file():
        return 0
    return sum(
        1 for line in Path(str(path)).read_text(encoding="utf-8").splitlines() if line.strip()
    )


Matcher = Callable[[object, object], bool]


def _matcher(kind: str) -> Matcher:
    if kind == "normalized_match":
        return lambda answer, expected: normalize_answer(answer) == normalize_answer(expected)
    return lambda answer, expected: str(answer).strip() == str(expected).strip()


def _outcome(response: ModelResponse | None, expected: object, match: Matcher) -> bool | None:
    """``None`` when there is no usable response (missing or errored) — never "wrong"."""
    if response is None or response.error is not None:
        return None
    if response.parsed_answer is None:
        return False
    return match(response.parsed_answer, expected)


@dataclass(frozen=True)
class _Paired:
    parents: tuple[str, ...]
    canonical: tuple[float, ...]
    transformed: tuple[float, ...]
    variants: int
    errored_variants: int


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


class _Analysis:
    """Scores, paired comparisons, and findings for one completed set of responses."""

    def __init__(
        self,
        spec: AuditSpec,
        benchmark: Benchmark,
        canonical: Sequence[ModelResponse],
        derived: Sequence[DerivedItem],
        transformed: Sequence[ModelResponse],
        seed: int,
    ) -> None:
        self.spec = spec
        self.benchmark = benchmark
        self.canonical = canonical
        self.derived = derived
        self.transformed = transformed
        self.seed = seed
        self.match = _matcher(benchmark.scoring.kind)
        self.external = benchmark.scoring.kind.startswith("external_")
        by_id = {response.item_id: response for response in canonical}
        self.canonical_outcomes = {
            item.id: _outcome(by_id.get(item.id), item.expected_output, self.match)
            for item in benchmark.items
        }
        self.transformed_by_id = {response.item_id: response for response in transformed}
        self.detector_specs: dict[str, DetectorSpec] = {}
        for detector in spec.detectors:
            if detector.enabled:
                self.detector_specs.setdefault(detector.type, detector)

    # -- pairing ---------------------------------------------------------------------
    def pair(self, derived: Sequence[DerivedItem]) -> _Paired:
        by_parent: dict[str, list[float]] = {}
        errored = 0
        variants = 0
        for value in derived:
            outcome = _outcome(
                self.transformed_by_id.get(value.item.id), value.item.expected_output, self.match
            )
            if outcome is None:
                errored += 1
                continue
            variants += 1
            by_parent.setdefault(value.transformation.parent_item_id, []).append(float(outcome))
        parents: list[str] = []
        left: list[float] = []
        right: list[float] = []
        for item in self.benchmark.items:
            values = by_parent.get(item.id)
            base = self.canonical_outcomes.get(item.id)
            if not values or base is None:
                continue
            parents.append(item.id)
            left.append(float(base))
            right.append(_mean(values))
        return _Paired(tuple(parents), tuple(left), tuple(right), variants, errored)

    def valid(self, families: frozenset[str] | None = None) -> list[DerivedItem]:
        return [
            value
            for value in self.derived
            if value.transformation.validation is ValidationStatus.VALID
            and (families is None or value.transformation.family in families)
        ]

    def paired_stats(self, paired: _Paired) -> dict[str, Any]:
        details: dict[str, Any] = {
            "parent_item_count": len(paired.parents),
            "variant_count": paired.variants,
            "errored_variant_count": paired.errored_variants,
        }
        if not paired.parents:
            return details
        canonical_score = _mean(paired.canonical)
        transformed_score = _mean(paired.transformed)
        low, high = paired_bootstrap_gap(paired.canonical, paired.transformed, seed=self.seed)
        details.update(
            {
                "canonical_score": canonical_score,
                "transformed_score": transformed_score,
                "gap": canonical_score - transformed_score,
                "ci": [low, high],
                "permutation_p_value": paired_permutation_p_value(
                    paired.canonical, paired.transformed, seed=self.seed
                ),
                "mcnemar": mcnemar_exact(
                    [value == 1.0 for value in paired.canonical],
                    [value >= 0.5 for value in paired.transformed],
                ),
            }
        )
        return details

    # -- scores ----------------------------------------------------------------------
    def score(self) -> ScoreSummary:
        reported = self.spec.report.get("reported_score")
        reported_score = float(reported) if isinstance(reported, int | float) else None
        if self.external:
            return ScoreSummary(reported_score=reported_score)
        scored = [value for value in self.canonical_outcomes.values() if value is not None]
        canonical_score = _mean([float(value) for value in scored]) if scored else None
        stats = self.paired_stats(self.pair(self.valid()))
        return ScoreSummary(
            reported_score=reported_score,
            canonical_reproduced_score=canonical_score,
            robust_score=stats.get("transformed_score"),
            robustness_gap=stats.get("gap"),
            ci=tuple(stats["ci"]) if "ci" in stats else None,
        )

    # -- findings --------------------------------------------------------------------
    def requested(self) -> list[str]:
        names = list(self.detector_specs)
        if self.derived and "perturbation" not in names:
            names.insert(0, "perturbation")  # the headline robustness result always reports
        return names

    def findings(self, *, token_probabilities: bool) -> list[DetectorFinding]:
        drafts: list[dict[str, Any]] = []
        for name in self.requested():
            if name in _PAIRED_DETECTORS:
                drafts.append(self._paired_finding(name))
            elif name == "probability":
                drafts.append(self._probability(token_probabilities))
            elif name == "exact_match":
                drafts.append(self._exact_match())
            else:
                drafts.append(
                    _not_run(
                        name,
                        _DETECTOR_HYPOTHESES[name],
                        "requirements not supplied in initial adapter run",
                        "This audit configuration did not provide the required data or access.",
                        assumptions=(
                            "Required matched controls and detector inputs are configured.",
                        ),
                    )
                )
        self._correct_and_classify(drafts)
        return [DetectorFinding.model_validate(draft) for draft in drafts]

    def _config(self, name: str, key: str, default: float) -> float:
        detector = self.detector_specs.get(name)
        value = detector.config.get(key, default) if detector else default
        return float(value) if isinstance(value, int | float) else default

    def _paired_finding(self, name: str) -> dict[str, Any]:
        families, hypothesis = _PAIRED_DETECTORS[name]
        if self.external:
            return _not_run(
                name,
                hypothesis,
                "requires an external grader",
                f"{self.benchmark.scoring.kind} scoring is not exact-match; Veritas does not "
                "execute code or repository harnesses.",
            )
        selected = self.valid(families)
        if not selected:
            wanted = (
                "validated transformations" if families is None else ", ".join(sorted(families))
            )
            return _not_run(
                name,
                hypothesis,
                "required transformation family unavailable",
                f"No applicable {wanted} were configured for these items.",
            )
        details = self.paired_stats(self.pair(selected))
        if name == "perturbation":
            details["families"] = self._family_breakdown()
        if not details.get("parent_item_count"):
            return _not_run(
                name,
                hypothesis,
                "no scorable canonical/variant pairs",
                "Every paired response errored or was missing.",
                details=details,
            )
        return {
            "detector_id": name,
            "detector_version": "2",
            "hypothesis": hypothesis,
            "evidence_type": "paired parent-item accuracy (canonical minus validated variants)",
            "statistic": details["gap"],
            "effect_size": details["gap"],
            "ci": tuple(details["ci"]),
            "p_value": details["permutation_p_value"],
            "assumptions": (
                "Validated transformations preserve task content and intended difficulty.",
            ),
            "alternative_explanations": (
                "parser sensitivity",
                "ordinary distribution shift",
                "stochastic variance",
            ),
            "calibration": "paired sign-flip permutation test; Benjamini-Hochberg across findings",
            "details": details,
        }

    def _family_breakdown(self) -> dict[str, Any]:
        breakdown: dict[str, Any] = {}
        for family in sorted({value.transformation.family for value in self.derived}):
            members = [value for value in self.derived if value.transformation.family == family]
            valid = [
                value
                for value in members
                if value.transformation.validation is ValidationStatus.VALID
            ]
            unvalidated = [
                value
                for value in members
                if value.transformation.validation is not ValidationStatus.VALID
            ]
            stats = self.paired_stats(self.pair(valid if valid else unvalidated))
            breakdown[family] = {
                "validation": "valid" if valid else "unvalidated",
                "included_in_robust_score": bool(valid),
                "parent_item_count": stats["parent_item_count"],
                "variant_count": stats["variant_count"],
                "unvalidated_variant_count": len(unvalidated) if valid else len(members),
                "transformed_score": stats.get("transformed_score"),
                "gap": stats.get("gap"),
            }
        return breakdown

    def _probability(self, token_probabilities: bool) -> dict[str, Any]:
        hypothesis = "exposure evidence from token probabilities"
        if not token_probabilities:
            return _not_run(
                "probability",
                hypothesis,
                "token likelihood",
                "API does not expose log probabilities.",
                assumptions=("Token probabilities are available.",),
            )
        sequences = [
            response.token_logprobs
            for response in self.canonical
            if response.token_logprobs and response.error is None
        ]
        if not sequences:
            return _not_run(
                "probability",
                hypothesis,
                "token likelihood",
                "Adapter declared support but returned no log probabilities.",
                assumptions=("Responses contain generated-token log probabilities.",),
            )
        nll = [-sum(values) / len(values) for values in sequences]
        return {
            "detector_id": "probability",
            "detector_version": "1",
            "hypothesis": hypothesis,
            "evidence_type": "mean generated-token negative log likelihood",
            "statistic": sum(nll) / len(nll),
            "direction": EvidenceDirection.INCONCLUSIVE,
            "strength": EvidenceStrength.INCONCLUSIVE,
            "calibration": "uncalibrated_without_matched_member/non-member_controls",
            "assumptions": ("Generated-token likelihood is comparable across items.",),
            "alternative_explanations": ("domain familiarity", "model confidence", "tokenization"),
            "details": {"n_items_with_logprobs": len(nll)},
        }

    def _exact_match(self) -> dict[str, Any]:
        hypothesis = "exact public-reference overlap"
        raw = self.spec.runtime.get("reference_texts")
        if not isinstance(raw, list) or not raw:
            return _not_run(
                "exact_match",
                hypothesis,
                "verified lexical prompt overlap",
                "No reference corpus was supplied (runtime.reference_texts); absence of a "
                "comparison is not absence of overlap.",
                assumptions=("A relevant reference corpus is supplied.",),
            )
        references = {normalize_answer(value) for value in raw}
        matched = tuple(
            item.id
            for item in self.benchmark.items
            if normalize_answer(prompt_text(item)) in references
        )
        return {
            "detector_id": "exact_match",
            "detector_version": "2",
            "hypothesis": hypothesis,
            "evidence_type": "verified lexical prompt overlap (whitespace- and case-normalized)",
            "statistic": float(len(matched)),
            "effect_size": len(matched) / len(self.benchmark.items),
            "direction": EvidenceDirection.SUPPORTS if matched else EvidenceDirection.INCONCLUSIVE,
            "strength": EvidenceStrength.DIRECT if matched else EvidenceStrength.INCONCLUSIVE,
            "item_ids": matched,
            "assumptions": (
                "Reference corpus is relevant and complete enough for this comparison.",
            ),
            "alternative_explanations": (
                "Publication overlap does not prove model training exposure.",
            ),
            "details": {"reference_count": len(references), "matched_count": len(matched)},
        }

    def _correct_and_classify(self, drafts: list[dict[str, Any]]) -> None:
        tested = [
            index
            for index, draft in enumerate(drafts)
            if draft.get("status", FindingStatus.COMPLETE) is FindingStatus.COMPLETE
            and draft.get("p_value") is not None
        ]
        corrected = benjamini_hochberg([float(drafts[index]["p_value"]) for index in tested])
        for index, value in zip(tested, corrected, strict=True):
            draft = drafts[index]
            draft["corrected_p_value"] = value
            name = draft["detector_id"]
            alpha = self._config(name, "alpha", DEFAULT_ALPHA)
            margin = self._config(name, "equivalence_margin", DEFAULT_EQUIVALENCE_MARGIN)
            minimum = int(self._config(name, "min_parent_items", DEFAULT_MIN_PARENT_ITEMS))
            details = draft["details"]
            low, high = details["ci"]
            if details["parent_item_count"] < minimum:
                direction, strength = EvidenceDirection.INCONCLUSIVE, EvidenceStrength.INCONCLUSIVE
                rule = f"fewer than {minimum} paired parent items"
            elif details["gap"] > 0 and low > 0 and value <= alpha:
                direction, strength = EvidenceDirection.SUPPORTS, EvidenceStrength.WEAK_INDIRECT
                rule = f"paired drop with interval above 0 and corrected p <= {alpha}"
            elif high < margin:
                direction, strength = EvidenceDirection.CONTRADICTS, EvidenceStrength.AGAINST
                rule = f"paired drop bounded below the {margin} equivalence margin"
            else:
                direction, strength = EvidenceDirection.INCONCLUSIVE, EvidenceStrength.INCONCLUSIVE
                rule = "interval is compatible with both no effect and a meaningful drop"
            draft["direction"] = direction
            draft["strength"] = strength
            details["decision_rule"] = rule

    # -- limitations -----------------------------------------------------------------
    def limitations(self) -> tuple[str, ...]:
        notes = [
            "Behavioral evidence cannot establish a closed model's training membership.",
            "Generated variants are reported separately by validation status; only validated "
            "variants enter the robust score.",
        ]
        failed = sum(1 for value in self.canonical_outcomes.values() if value is None)
        if failed:
            notes.append(
                f"{failed} canonical response(s) were missing or failed after retries and were "
                "excluded from scoring rather than counted as wrong."
            )
        failed_variants = sum(
            1
            for value in self.derived
            if _outcome(
                self.transformed_by_id.get(value.item.id), value.item.expected_output, self.match
            )
            is None
        )
        if failed_variants:
            notes.append(
                f"{failed_variants} transformed response(s) were missing or failed and were "
                "excluded from paired comparisons."
            )
        if self.spec.transformations:
            covered = {value.transformation.parent_item_id for value in self.derived}
            uncovered = sum(1 for item in self.benchmark.items if item.id not in covered)
            if uncovered:
                notes.append(
                    f"{uncovered} item(s) had no applicable transformation and contribute only "
                    "to the canonical score."
                )
            paired = len(self.pair(self.valid()).parents)
            if 0 < paired < DEFAULT_MIN_PARENT_ITEMS:
                notes.append(
                    f"Only {paired} paired item(s): paired findings stay inconclusive below "
                    f"{DEFAULT_MIN_PARENT_ITEMS}; audit more items for a decision."
                )
        if self.external:
            notes.append(
                f"Scoring kind {self.benchmark.scoring.kind!r} needs an external grader; "
                "accuracy-based scores and paired findings are not computed."
            )
        if self.spec.model.max_cost_usd is not None:
            notes.append(
                "max_cost_usd is recorded but not enforced (no provider price table); "
                "request_limit and token_limit bound spend."
            )
        return tuple(notes)


def _not_run(
    detector_id: str,
    hypothesis: str,
    evidence_type: str,
    reason: str,
    *,
    assumptions: tuple[str, ...] = (),
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "detector_id": detector_id,
        "detector_version": "2",
        "hypothesis": hypothesis,
        "status": FindingStatus.NOT_RUN,
        "evidence_type": evidence_type,
        "strength": EvidenceStrength.UNAVAILABLE,
        "assumptions": assumptions,
        "alternative_explanations": (reason,),
        "details": dict(details or {}),
    }


def _matrix(findings: Sequence[DetectorFinding]) -> tuple[EvidenceMatrixRow, ...]:
    by_id = {finding.detector_id: finding for finding in findings}
    rows: list[EvidenceMatrixRow] = []
    for hypothesis, detector_ids in _MATRIX:
        completed = [
            by_id[name]
            for name in detector_ids
            if name in by_id and by_id[name].status is FindingStatus.COMPLETE
        ]
        supporting = [f for f in completed if f.direction is EvidenceDirection.SUPPORTS]
        contradicting = [f for f in completed if f.direction is EvidenceDirection.CONTRADICTS]
        if supporting:
            confidence = min((f.strength for f in supporting), key=_STRENGTH_ORDER.index)
        elif contradicting:
            confidence = EvidenceStrength.AGAINST
        elif completed:
            confidence = EvidenceStrength.INCONCLUSIVE
        else:
            confidence = EvidenceStrength.UNAVAILABLE
        rows.append(
            EvidenceMatrixRow(
                hypothesis=hypothesis,
                supporting=tuple(f.detector_id for f in supporting),
                contradicting=tuple(f.detector_id for f in contradicting),
                unavailable=tuple(
                    name
                    for name in detector_ids
                    if name not in by_id or by_id[name].status is not FindingStatus.COMPLETE
                ),
                confidence=confidence,
                assumptions=tuple(
                    dict.fromkeys(assumption for f in completed for assumption in f.assumptions)
                ),
            )
        )
    return tuple(rows)
