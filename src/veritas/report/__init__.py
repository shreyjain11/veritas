"""Report rendering: JSON / Markdown / HTML + figures, all pure on an AuditReport.

Limitations are a first-class, hashed field of the AuditReport (stamped by
``assemble_report``); the renderers read ``report.limitations`` and never take
them as an argument.
"""

from __future__ import annotations

from veritas.report.figures import render_curve_svg
from veritas.report.html_report import render_html
from veritas.report.json_report import render_json
from veritas.report.limitations import collect_limitations
from veritas.report.markdown_report import render_markdown
from veritas.report.model import (
    assemble_detection_report,
    assemble_report,
    assemble_stratification_report,
    audit_hash_for,
)
from veritas.report.numbers import format_number

__all__ = [
    "assemble_detection_report",
    "assemble_report",
    "assemble_stratification_report",
    "audit_hash_for",
    "collect_limitations",
    "format_number",
    "render_curve_svg",
    "render_html",
    "render_json",
    "render_markdown",
]
