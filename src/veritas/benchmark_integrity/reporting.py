"""Deterministic cross-format renderers for schema-v2 audit reports."""

from __future__ import annotations

import html
import json

from veritas.benchmark_integrity.contracts import AuditReport, DetectorFinding


def render_json(report: AuditReport) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def render_markdown(report: AuditReport) -> str:
    score = report.score
    rows = "\n".join(_markdown_row(finding) for finding in report.findings)
    limitations = "\n".join(f"- {value}" for value in report.limitations)
    return (
        f"# Veritas benchmark-integrity audit: {report.benchmark.id}\n\n"
        f"- **schema:** {report.schema_version}\n- **audit hash:** `{report.audit_hash}`\n\n"
        "## Scores\n\n"
        f"- Canonical reproduced: {score.canonical_reproduced_score}\n"
        f"- Robust: {score.robust_score}\n- Robustness gap: {score.robustness_gap}\n\n"
        "## Findings\n\n| detector | status | evidence strength | effect size |\n"
        "| --- | --- | --- | --- |\n"
        f"{rows}\n\n## Limitations\n\n{limitations}\n"
    )


def render_html(report: AuditReport) -> str:
    findings = "".join(_html_row(finding) for finding in report.findings)
    limitations = "".join(f"<li>{html.escape(value)}</li>" for value in report.limitations)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>Veritas audit — {html.escape(report.benchmark.id)}</title></head><body>"
        f"<h1>{html.escape(report.benchmark.id)}</h1>"
        f"<p>schema {report.schema_version} · audit hash {report.audit_hash}</p>"
        "<h2>Scores</h2>"
        "<p>Canonical: "
        f"{report.score.canonical_reproduced_score}; Robust: {report.score.robust_score}; "
        f"Gap: {report.score.robustness_gap}</p>"
        "<h2>Findings</h2><table><thead><tr><th>Detector</th><th>Status</th><th>Strength</th><th>Effect</th></tr></thead>"
        f"<tbody>{findings}</tbody></table><h2>Limitations</h2><ul>{limitations}</ul></body></html>"
    )


def _markdown_row(finding: DetectorFinding) -> str:
    """Format a detector row without giving Markdown an unbounded text surface."""
    display = finding.effect_size if finding.effect_size is not None else "unavailable"
    return (
        f"| {finding.detector_id} | {finding.status.value} | {finding.strength.value} | {display} |"
    )


def _html_row(finding: DetectorFinding) -> str:
    display = finding.effect_size if finding.effect_size is not None else "unavailable"
    return (
        "<tr>"
        f"<td>{html.escape(finding.detector_id)}</td>"
        f"<td>{finding.status.value}</td>"
        f"<td>{finding.strength.value}</td><td>{display}</td></tr>"
    )
