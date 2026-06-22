"""Demonstration / reproduction datasets: manifests, fetching, and adapters.

This subpackage holds all benchmark/dataset specifics (CLAUDE.md principle #5).
Core Veritas never imports it; it depends on core, never the reverse.
"""

from __future__ import annotations

from veritas.demos.fetch import ChecksumMismatchError, fetch_dataset, verify_file
from veritas.demos.manifest import DatasetManifest, DataSource, SliceFile, load_manifest
from veritas.demos.overfitnn import overfitnn_predictions
from veritas.demos.ppi import PPIAdapter
from veritas.demos.proteingym import ProteinGymAdapter
from veritas.demos.regulatory_dna import RegulatoryDNAAdapter

__all__ = [
    "ChecksumMismatchError",
    "DataSource",
    "DatasetManifest",
    "PPIAdapter",
    "ProteinGymAdapter",
    "RegulatoryDNAAdapter",
    "SliceFile",
    "fetch_dataset",
    "load_manifest",
    "overfitnn_predictions",
    "verify_file",
]
