"""Veritas data contracts: every schema crossing a module boundary lives here."""

from __future__ import annotations

from veritas.contracts.audit_config import AuditConfig, DetectorConfig
from veritas.contracts.audit_inputs import AuditInputs
from veritas.contracts.benchmark import Benchmark, MetricSpec, SplitSpec
from veritas.contracts.contamination import ContaminationEdge, ContaminationGraph
from veritas.contracts.enums import (
    CombinePolicy,
    DeLeakPolicy,
    DetectorKind,
    MetricName,
    Partition,
    ReportKind,
    ResultStatus,
    SeqType,
    SplitRole,
)
from veritas.contracts.eval_item import EvalItem
from veritas.contracts.predictions import PredictionRecord, PredictionSet
from veritas.contracts.provenance import ProvenanceRecord
from veritas.contracts.reference_item import ReferenceItem
from veritas.contracts.report import (
    AuditReport,
    DetectorCell,
    LeakageSplit,
    LeakageSummary,
    Limitation,
    StratumResult,
    TracedValue,
)

__all__ = [
    "AuditConfig",
    "AuditInputs",
    "AuditReport",
    "Benchmark",
    "CombinePolicy",
    "ContaminationEdge",
    "ContaminationGraph",
    "DeLeakPolicy",
    "DetectorCell",
    "DetectorConfig",
    "DetectorKind",
    "EvalItem",
    "LeakageSplit",
    "LeakageSummary",
    "Limitation",
    "MetricName",
    "MetricSpec",
    "Partition",
    "PredictionRecord",
    "PredictionSet",
    "ProvenanceRecord",
    "ReferenceItem",
    "ReportKind",
    "ResultStatus",
    "SeqType",
    "SplitRole",
    "SplitSpec",
    "StratumResult",
    "TracedValue",
]
