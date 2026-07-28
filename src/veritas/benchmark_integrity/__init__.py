"""Veritas v2 benchmark-integrity audit system.

This package is deliberately independent of :mod:`veritas.contamination`: the
former sequence auditor remains available as the legacy biological domain.
"""

from __future__ import annotations

from veritas.benchmark_integrity.contracts import AuditReport, AuditSpec, Benchmark, BenchmarkItem
from veritas.benchmark_integrity.reporting import render_html, render_json, render_markdown
from veritas.benchmark_integrity.service import audit, inspect_audit

__all__ = [
    "AuditReport",
    "AuditSpec",
    "Benchmark",
    "BenchmarkItem",
    "audit",
    "inspect_audit",
    "render_html",
    "render_json",
    "render_markdown",
]
