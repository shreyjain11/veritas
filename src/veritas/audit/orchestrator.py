"""run_audit: the single source of truth that drives the whole audit pipeline.

config -> contamination -> de-leak -> honest metrics -> stratification -> assembled
report. Every MetricEstimate produced inside the pipeline leaves wrapped in a
TracedValue whose provenance_ref is the run's ProvenanceRecord content id, so no
number escapes un-stamped (req C). Pinned versions come from the *declared* config,
never from probing the binary about to run, so a drifted binary surfaces as a
mismatch.
"""

from __future__ import annotations

from collections import defaultdict

from veritas.audit.pipeline_steps import DetectorFactory, detect, rescore, stratify
from veritas.contamination.graph import contaminated_eval_ids
from veritas.contamination.registry import get_detector
from veritas.contracts import (
    AuditConfig,
    AuditInputs,
    AuditReport,
    ContaminationGraph,
    DetectorKind,
    EvalItem,
    LeakageSummary,
    StratumResult,
    TracedValue,
)
from veritas.metrics.result import MetricEstimate
from veritas.provenance import audit_hash, build_provenance_record, capture_tool_versions
from veritas.provenance.tool_versions import Runner
from veritas.report import assemble_report
from veritas.stratify import StratifiedCurve, detect_silent_failures

_PREFILTERED_KINDS = frozenset({DetectorKind.SEQUENCE, DetectorKind.FAMILY})


def _trace(name: str, estimate: MetricEstimate, provenance_ref: str) -> TracedValue:
    return TracedValue(
        name=name,
        value=estimate.value,
        status=estimate.status,
        provenance_ref=provenance_ref,
        ci_low=estimate.ci_low,
        ci_high=estimate.ci_high,
    )


def _leakage_summary(graph: ContaminationGraph, eval_items: tuple[EvalItem, ...]) -> LeakageSummary:
    # Count only contamination of items actually in the benchmark: a precomputed graph
    # may reference ids the benchmark doesn't contain, and those are not de-leaked, so
    # counting them would make n_contaminated disagree with the honest set.
    eval_ids = {item.id for item in eval_items}
    per_detector: defaultdict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        if edge.eval_id in eval_ids:
            per_detector[edge.detector_id].add(edge.eval_id)
    return LeakageSummary(
        n_eval=len(eval_items),
        n_contaminated=len(contaminated_eval_ids(graph) & eval_ids),
        per_detector={detector: len(ids) for detector, ids in per_detector.items()},
    )


def _strata(
    axes: tuple[str, ...], curves: tuple[StratifiedCurve, ...], provenance_ref: str
) -> tuple[StratumResult, ...]:
    strata: list[StratumResult] = []
    for axis_name, curve in zip(axes, curves, strict=True):
        flagged = {flag.bucket_index for flag in detect_silent_failures(curve)}
        for bucket in curve.buckets:
            strata.append(
                StratumResult(
                    axis_name=axis_name,
                    bucket_index=bucket.index,
                    bucket_label=f"[{bucket.lo}, {bucket.hi})",
                    n=bucket.n,
                    metric=_trace(f"{axis_name}#{bucket.index}", bucket.estimate, provenance_ref),
                    is_silent_failure=bucket.index in flagged,
                )
            )
    return tuple(strata)


def run_audit(
    config: AuditConfig,
    inputs: AuditInputs,
    *,
    detector_factory: DetectorFactory = get_detector,
    version_runner: Runner | None = None,
) -> AuditReport:
    graph = detect(config, inputs, detector_factory=detector_factory)
    comparison = rescore(config, inputs, graph)
    curves = stratify(config, inputs, graph)

    # Record the exact binary each detector resolved at construction (security: the
    # absolute path actually run, not a PATH-dependent name).
    resolved_binaries: dict[str, str] = {}
    for detector_config in config.detectors:
        detector = detector_factory(detector_config.name)
        if detector.binary_path is not None:
            resolved_binaries[detector_config.name] = detector.binary_path

    tool_names = tuple(dict.fromkeys(detector.name for detector in config.detectors))
    runtime_versions = (
        capture_tool_versions(tool_names)
        if version_runner is None
        else capture_tool_versions(tool_names, runner=version_runner)
    )

    provenance = build_provenance_record(
        inputs={
            "benchmark": inputs.benchmark.model_dump(mode="json"),
            "reference": [item.model_dump(mode="json") for item in inputs.reference_items],
        },
        params={**config.model_dump(mode="json"), "resolved_binaries": resolved_binaries},
        seed=config.seed,
        # Pinned versions are DECLARED (config), not probed from the running binary.
        pinned_versions=dict(config.pinned_versions),
        runtime_versions=runtime_versions,
    )
    provenance_ref = audit_hash(provenance)

    prefilter_enabled = any(detector.kind in _PREFILTERED_KINDS for detector in config.detectors)
    return assemble_report(
        benchmark_name=inputs.benchmark.name,
        reported=_trace("reported", comparison.reported, provenance_ref),
        honest=_trace("honest", comparison.honest, provenance_ref),
        delta=_trace("delta", comparison.delta, provenance_ref),
        leakage=_leakage_summary(graph, inputs.benchmark.eval_items),
        provenance=provenance,
        prefilter_enabled=prefilter_enabled,
        stratification=_strata(config.stratify_axes, curves, provenance_ref),
        status=comparison.status,
    )
