"""File-based audit runners shared by the CLI and MCP layers.

Both front-ends call these, so a given audit is byte-identical whether invoked via
`veritas ...` or the MCP tools (CLI==MCP parity), with no duplicated logic.
"""

from __future__ import annotations

from pathlib import Path

from veritas.audit.io_helpers import (
    PrecomputedDetector,
    load_config,
    load_graph,
    placeholder_reference,
)
from veritas.audit.orchestrator import run_audit
from veritas.audit.pipeline_steps import detect
from veritas.contracts import (
    AuditConfig,
    AuditInputs,
    AuditReport,
    Benchmark,
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
    EvalItem,
    MetricName,
    MetricSpec,
    SeqType,
    SplitSpec,
)
from veritas.io.fasta import read_fasta
from veritas.io.loaders import load_benchmark, load_reference_set


def audit_from_files(
    *,
    sequences: Path,
    table: Path,
    reference: Path,
    config: Path,
    seq_type: SeqType,
    metric: MetricName,
) -> AuditReport:
    benchmark = load_benchmark(
        sequences,
        table,
        seq_type=seq_type,
        metric=MetricSpec(name=metric),
        split=SplitSpec(name="audit", kind="holdout"),
    )
    inputs = AuditInputs(
        benchmark=benchmark, reference_items=load_reference_set(reference, seq_type=seq_type)
    )
    return run_audit(load_config(config), inputs)


def detect_from_files(
    *, sequences: Path, reference: Path, config: Path, seq_type: SeqType
) -> ContaminationGraph:
    eval_items = tuple(
        EvalItem(id=record.id, seq_type=seq_type, sequence=record.sequence, label=0.0)
        for record in read_fasta(sequences, seq_type=seq_type)
    )
    benchmark = Benchmark(
        name=sequences.stem,
        eval_items=eval_items,
        split=SplitSpec(name="leakage", kind="holdout"),
        metric=MetricSpec(name=MetricName.ACCURACY),
    )
    inputs = AuditInputs(
        benchmark=benchmark, reference_items=load_reference_set(reference, seq_type=seq_type)
    )
    return detect(load_config(config), inputs)


def audit_on_precomputed_graph(
    *,
    sequences: Path,
    table: Path,
    graph: Path,
    seq_type: SeqType,
    metric: MetricName,
    axes: tuple[str, ...],
) -> AuditReport:
    benchmark = load_benchmark(
        sequences,
        table,
        seq_type=seq_type,
        metric=MetricSpec(name=metric),
        split=SplitSpec(name="precomputed", kind="precomputed"),
    )
    inputs = AuditInputs(benchmark=benchmark, reference_items=(placeholder_reference(seq_type),))
    loaded = load_graph(graph)
    config = AuditConfig(
        detectors=(
            DetectorConfig(kind=DetectorKind.SEQUENCE, name="precomputed", identity_threshold=0.0),
        ),
        seed=1729,
        stratify_axes=axes,
    )
    return run_audit(config, inputs, detector_factory=lambda _name: PrecomputedDetector(loaded))
