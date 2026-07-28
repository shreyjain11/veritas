"""Compatibility namespace for the preserved biological leakage auditor.

The implementation remains in its validated v1 modules during the staged move;
new callers should use this namespace rather than depending on the v2 core.
"""

from veritas.audit.orchestrator import run_audit
from veritas.contracts import (
    AuditConfig,
    AuditInputs,
    AuditReport,
    Benchmark,
    EvalItem,
    ReferenceItem,
)

__all__ = [
    "AuditConfig",
    "AuditInputs",
    "AuditReport",
    "Benchmark",
    "EvalItem",
    "ReferenceItem",
    "run_audit",
]
