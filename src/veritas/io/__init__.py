"""IO loaders and pluggable adapters for Veritas."""

from __future__ import annotations

from veritas.io.adapters import BenchmarkAdapter, ModelAdapter, ReferenceAdapter
from veritas.io.fasta import FastaRecord, parse_fasta, read_fasta
from veritas.io.loaders import load_benchmark, load_reference_set
from veritas.io.predictions_io import load_predictions
from veritas.io.splits import load_splits

__all__ = [
    "BenchmarkAdapter",
    "FastaRecord",
    "ModelAdapter",
    "ReferenceAdapter",
    "load_benchmark",
    "load_predictions",
    "load_reference_set",
    "load_splits",
    "parse_fasta",
    "read_fasta",
]
