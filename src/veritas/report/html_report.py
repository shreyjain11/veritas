"""Self-contained HTML report (jinja2, autoescaped; inline CSS, no JS/CDN)."""

from __future__ import annotations

import jinja2

from veritas.contracts import AuditReport
from veritas.report._context import build_context

_TEMPLATE = jinja2.Environment(autoescape=True, trim_blocks=True, lstrip_blocks=True).from_string(
    """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Veritas Audit Report - {{ benchmark_name }}</title>
<style>
body { font-family: sans-serif; margin: 2rem; color: #111; }
table { border-collapse: collapse; }
th, td { border: 1px solid #ccc; padding: 4px 8px; }
.warn { color: #b00; font-weight: bold; }
</style>
</head>
<body>
<h1>Veritas Audit Report - {{ benchmark_name }}</h1>
<p><strong>audit_hash:</strong> <code>{{ audit_hash }}</code></p>
<p><strong>status:</strong> {{ status }}</p>
<h2>Metrics</h2>
<table>
<tr><th>metric</th><th>value</th><th>95% CI</th><th>provenance</th></tr>
{% for m in metrics %}
<tr>
<td>{{ m.label }}</td>
<td>{{ m.display }}</td>
<td>{{ m.ci }}</td>
<td><code>{{ m.provenance_ref }}</code></td>
</tr>
{% endfor %}
</table>
<h2>Leakage</h2>
<ul>
<li>eval items: {{ leakage.n_eval }}</li>
<li>contaminated: {{ leakage.n_contaminated }} (fraction {{ leakage.fraction }})</li>
{% for name, count in leakage.per_detector %}
<li>detector {{ name }}: {{ count }}</li>
{% endfor %}
</ul>
<h2>Provenance</h2>
<ul>
<li>seed: {{ seed }}</li>
{% for name, ver in pinned_versions %}
<li>{{ name }} pinned: {{ ver }}</li>
{% endfor %}
{% for name, ver in runtime_versions %}
<li>{{ name }} runtime: {{ ver }}</li>
{% endfor %}
</ul>
{% if version_mismatches %}
<p class="warn">Version mismatch: {{ version_mismatches | join(", ") }}</p>
{% endif %}
<h2>Limitations</h2>
{% for lim in limitations %}
<h3>{{ lim.title }}</h3>
<p>{{ lim.detail }}</p>
{% endfor %}
{% if stratification %}
<h2>Stratified robustness</h2>
<table>
<tr>
<th>axis</th><th>bucket</th><th>n</th><th>value</th><th>silent failure</th>
</tr>
{% for s in stratification %}
<tr>
<td>{{ s.axis_name }}</td>
<td>{{ s.label }}</td>
<td>{{ s.n }}</td>
<td>{{ s.display }}</td>
<td>{{ s.silent_failure }}</td>
</tr>
{% endfor %}
</table>
{% endif %}
</body>
</html>
"""
)


def render_html(report: AuditReport) -> str:
    return _TEMPLATE.render(**build_context(report))
