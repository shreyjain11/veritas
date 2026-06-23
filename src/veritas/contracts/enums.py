"""Enumerations shared across contracts. String values are part of the serialization API."""

from __future__ import annotations

from enum import StrEnum


class SeqType(StrEnum):
    PROTEIN = "protein"
    NUCLEOTIDE = "nucleotide"


class DetectorKind(StrEnum):
    SEQUENCE = "sequence"
    FAMILY = "family"
    STRUCTURE = "structure"


class DeLeakPolicy(StrEnum):
    DROP = "drop"
    STRATIFY = "stratify"
    REWEIGHT = "reweight"


class CombinePolicy(StrEnum):
    UNION = "union"
    INTERSECT = "intersect"


class MetricName(StrEnum):
    AUROC = "auroc"
    AUPRC = "auprc"
    SPEARMAN = "spearman"
    PEARSON = "pearson"
    ACCURACY = "accuracy"
    MCC = "mcc"
    F1 = "f1"


class ResultStatus(StrEnum):
    OK = "ok"
    INSUFFICIENT_CLEAN_DATA = "insufficient_clean_data"
    UNDEFINED_METRIC = "undefined_metric"


class ReportKind(StrEnum):
    """What an AuditReport carries (the wire-format discriminator).

    ``metric_audit`` is the reported-vs-honest audit (the metric slots are present);
    ``detection`` carries a leakage splits-matrix and no metric (no model was scored);
    ``stratification`` carries only a performance-by-difficulty curve. The kind is part
    of the hashed content, and a validator forbids fabricating a metric for the
    non-metric kinds (their reported/honest/delta must be null).
    """

    METRIC_AUDIT = "metric_audit"
    DETECTION = "detection"
    STRATIFICATION = "stratification"


class SplitRole(StrEnum):
    """The intent of a split in a detection report's matrix (drives viewer emphasis)."""

    DEMONSTRATION = "demonstration"
    CONTROL = "control"
    FINDING = "finding"


class Partition(StrEnum):
    TRAIN = "train"
    EVAL = "eval"
    REFERENCE = "reference"
