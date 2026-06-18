"""Audit orchestration: the single source of truth for the CLI and MCP layers."""

from __future__ import annotations

from veritas.audit.orchestrator import run_audit
from veritas.audit.pipeline_steps import detect, rescore, stratify

__all__ = ["detect", "rescore", "run_audit", "stratify"]
