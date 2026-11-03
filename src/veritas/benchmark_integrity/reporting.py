"""Deterministic cross-format renderers for schema-v2 audit reports."""

from __future__ import annotations

import html
import json

from veritas.benchmark_integrity.contracts import AuditReport, DetectorFinding, ScoreSummary


def render_json(report: AuditReport) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _pct(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return "unavailable"
    return f"{value * 100:+.1f}%" if signed else f"{value * 100:.1f}%"


def _interval(ci: tuple[float, float] | None) -> str:
    return "—" if ci is None else f"{_pct(ci[0], signed=True)} to {_pct(ci[1], signed=True)}"


def _p(value: float | None) -> str:
    return "—" if value is None else f"{value:.3g}"


def _verdict(finding: DetectorFinding) -> str:
    if finding.status.value != "complete":
        return finding.status.value.replace("_", " ")
    return f"{finding.direction.value} ({finding.strength.value.replace('_', ' ')})"


def _score_rows(score: ScoreSummary) -> list[tuple[str, str]]:
    return [
        ("Reported", _pct(score.reported_score)),
        ("Canonical reproduced", _pct(score.canonical_reproduced_score)),
        ("Robust (validated variants)", _pct(score.robust_score)),
        ("Robustness gap", _pct(score.robustness_gap, signed=True)),
        ("Gap 95% interval", _interval(score.ci)),
    ]


def _cell(value: str) -> str:
    """Escape a Markdown table cell so report text cannot break the table."""
    return value.replace("|", "\\|").replace("\n", " ")


def render_markdown(report: AuditReport) -> str:
    score_lines = "\n".join(f"- **{label}:** {value}" for label, value in _score_rows(report.score))
    rows = "\n".join(
        f"| {_cell(f.detector_id)} | {_cell(_verdict(f))} | "
        f"{_pct(f.effect_size, signed=True) if f.effect_size is not None else '—'} | "
        f"{_interval(f.ci)} | {_p(f.corrected_p_value or f.p_value)} |"
        for f in report.findings
    )
    matrix = "\n".join(
        f"| {_cell(r.hypothesis)} | {_cell(', '.join(r.supporting) or '—')} | "
        f"{_cell(', '.join(r.contradicting) or '—')} | "
        f"{_cell(', '.join(r.unavailable) or '—')} | {r.confidence.value} |"
        for r in report.evidence_matrix
    )
    limitations = "\n".join(f"- {value}" for value in report.limitations)
    model = report.provenance.model
    return (
        f"# Veritas benchmark-integrity audit: {report.benchmark.id}\n\n"
        f"- **schema:** {report.schema_version}\n"
        f"- **model:** `{model.id}` via `{model.adapter}`\n"
        f"- **items:** {len(report.benchmark.items)} canonical, "
        f"{len(report.transformations)} transformed\n"
        f"- **audit hash:** `{report.audit_hash}`\n\n"
        f"## Scores\n\n{score_lines}\n\n"
        "## Findings\n\n| detector | verdict | effect | 95% interval | p (BH) |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{rows}\n\n"
        "## Evidence matrix\n\n| hypothesis | supporting | contradicting | unavailable | "
        "confidence |\n| --- | --- | --- | --- | --- |\n"
        f"{matrix}\n\n## Limitations\n\n{limitations}\n"
    )


_STYLE = (
    "body{font:15px/1.5 system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;"
    "color:#1b1f24}table{border-collapse:collapse;width:100%;margin:1rem 0}"
    "th,td{border:1px solid #d0d7de;padding:.4rem .6rem;text-align:left;vertical-align:top}"
    "th{background:#f6f8fa}code{font-size:.85em;word-break:break-all}"
    "@media (prefers-color-scheme:dark){body{background:#0d1117;color:#e6edf3}"
    "th{background:#161b22}th,td{border-color:#30363d}}"
)


def render_html(report: AuditReport) -> str:
    esc = html.escape
    scores = "".join(
        f"<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>"
        for label, value in _score_rows(report.score)
    )
    findings = "".join(
        "<tr>"
        f"<td>{esc(f.detector_id)}</td><td>{esc(_verdict(f))}</td>"
        f"<td>{esc(_pct(f.effect_size, signed=True) if f.effect_size is not None else '—')}</td>"
        f"<td>{esc(_interval(f.ci))}</td><td>{esc(_p(f.corrected_p_value or f.p_value))}</td>"
        f"<td>{esc(f.hypothesis)}</td></tr>"
        for f in report.findings
    )
    matrix = "".join(
        f"<tr><td>{esc(r.hypothesis)}</td><td>{esc(', '.join(r.supporting) or '—')}</td>"
        f"<td>{esc(', '.join(r.contradicting) or '—')}</td>"
        f"<td>{esc(', '.join(r.unavailable) or '—')}</td><td>{esc(r.confidence.value)}</td></tr>"
        for r in report.evidence_matrix
    )
    limitations = "".join(f"<li>{esc(value)}</li>" for value in report.limitations)
    model = report.provenance.model
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Veritas audit — {esc(report.benchmark.id)}</title><style>{_STYLE}</style></head>"
        f"<body><h1>{esc(report.benchmark.id)}</h1>"
        f"<p>Model <code>{esc(model.id)}</code> via {esc(model.adapter)} · "
        f"{len(report.benchmark.items)} canonical items, {len(report.transformations)} variants</p>"
        f"<p>schema {esc(report.schema_version)} · audit hash <code>{esc(report.audit_hash)}</code>"
        "</p><h2>Scores</h2><table><tbody>"
        f"{scores}</tbody></table><h2>Findings</h2><table><thead><tr><th>Detector</th>"
        "<th>Verdict</th><th>Effect</th><th>95% interval</th><th>p (BH)</th><th>Hypothesis</th>"
        f"</tr></thead><tbody>{findings}</tbody></table><h2>Evidence matrix</h2><table><thead>"
        "<tr><th>Hypothesis</th><th>Supporting</th><th>Contradicting</th><th>Unavailable</th>"
        f"<th>Confidence</th></tr></thead><tbody>{matrix}</tbody></table>"
        f"<h2>Limitations</h2><ul>{limitations}</ul></body></html>"
    )
