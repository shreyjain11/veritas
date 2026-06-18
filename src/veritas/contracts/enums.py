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


class Partition(StrEnum):
    TRAIN = "train"
    EVAL = "eval"
    REFERENCE = "reference"
