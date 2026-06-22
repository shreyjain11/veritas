"""Independently-callable pipeline stages: detect -> rescore -> stratify.

These are the reusable building blocks the CLI subcommands call directly; the
orchestrator chains them into a full audit. Each is pure given its inputs and the
injected detector factory.
"""

from __future__ import annotations

from collections.abc import Callable

from veritas.contamination.base import ContaminationDetector
from veritas.contamination.compose import combine
from veritas.contamination.registry import get_detector
from veritas.contracts import (
    AuditConfig,
    AuditInputs,
    Benchmark,
    ContaminationGraph,
    EvalItem,
)
from veritas.metrics import HonestComparison, compute_honest
from veritas.stratify import (
    StratifiedCurve,
    categorical_performance_curve,
    fixed_bins,
    identity_to_nearest_reference,
    label_class,
    metadata_category,
    performance_curve,
)

DetectorFactory = Callable[[str], ContaminationDetector]

#: Fixed number of difficulty buckets per (numeric) stratification axis.
_N_BINS = 4

#: A ``metadata:<key>`` axis buckets eval items by the categorical EvalItem.metadata[key].
_METADATA_PREFIX = "metadata:"


def detect(
    config: AuditConfig,
    inputs: AuditInputs,
    *,
    detector_factory: DetectorFactory = get_detector,
) -> ContaminationGraph:
    """Run every configured detector and compose their graphs per the combine policy."""
    graphs = [
        detector_factory(detector_config.name).detect(
            inputs.benchmark.eval_items, inputs.reference_items, detector_config
        )
        for detector_config in config.detectors
    ]
    return combine(graphs, config.combine_policy)


def rescore(
    config: AuditConfig, inputs: AuditInputs, graph: ContaminationGraph
) -> HonestComparison:
    """Reported-vs-honest comparison after de-leaking against ``graph``."""
    return compute_honest(
        inputs.benchmark.eval_items,
        graph,
        inputs.benchmark.metric,
        policy=config.deleak_policy,
        bootstrap_n=config.bootstrap_n,
        ci_level=config.ci_level,
        seed=config.seed,
    )


def _axis_values(
    axis_name: str, eval_items: tuple[EvalItem, ...], graph: ContaminationGraph
) -> dict[str, float]:
    if axis_name == "identity_to_nearest_reference":
        return identity_to_nearest_reference(eval_items, graph)
    if axis_name == "label_class":
        return label_class(eval_items)
    raise ValueError(f"unknown stratification axis: {axis_name!r}")


def _curve_for_axis(
    axis_name: str, benchmark: Benchmark, graph: ContaminationGraph, config: AuditConfig
) -> StratifiedCurve:
    if axis_name.startswith(_METADATA_PREFIX):
        key = axis_name[len(_METADATA_PREFIX) :]
        if not key:
            raise ValueError(f"metadata stratification axis needs a key: {axis_name!r}")
        return categorical_performance_curve(
            benchmark.eval_items,
            metadata_category(benchmark.eval_items, key),
            benchmark.metric,
            axis_name=axis_name,
            seed=config.seed,
            n_bootstrap=config.bootstrap_n,
            ci_level=config.ci_level,
        )
    axis_values = _axis_values(axis_name, benchmark.eval_items, graph)
    return performance_curve(
        benchmark.eval_items,
        axis_values,
        fixed_bins(_N_BINS, lo=0.0, hi=1.0),
        benchmark.metric,
        axis_name=axis_name,
        seed=config.seed,
        n_bootstrap=config.bootstrap_n,
        ci_level=config.ci_level,
    )


def stratify(
    config: AuditConfig, inputs: AuditInputs, graph: ContaminationGraph
) -> tuple[StratifiedCurve, ...]:
    """One performance-vs-difficulty curve per configured axis (empty if none)."""
    return tuple(
        _curve_for_axis(axis_name, inputs.benchmark, graph, config)
        for axis_name in config.stratify_axes
    )
