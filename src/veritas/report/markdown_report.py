"""Human-readable Markdown report (jinja2; deterministic; structure-safe).

Markdown is not auto-escaped, so free-text/user-controlled values (benchmark name,
detector & tool names, provenance refs, limitation text) go through md_escape to keep
pipes/backticks/newlines from corrupting tables or headings. Internally-generated
fields (numbers, fixed labels, validated axis names) are already safe.
"""

from __future__ import annotations

import jinja2

from veritas.contracts import AuditReport
from veritas.report._context import build_context
from veritas.report.numbers import md_escape

_ENV = jinja2.Environment(
    autoescape=False, trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True
)
_ENV.filters["md_escape"] = md_escape

_TEMPLATE = _ENV.from_string(
    """# Veritas Audit Report - {{ benchmark_name | md_escape }}

- **audit_hash:** `{{ audit_hash }}`
- **status:** {{ status }}

## Metrics

| metric | value | 95% CI | provenance |
| --- | --- | --- | --- |
{% for m in metrics %}
| {{ m.label }} | {{ m.display }} | {{ m.ci }} | `{{ m.provenance_ref | md_escape }}` |
{% endfor %}

## Leakage

- eval items: {{ leakage.n_eval }}
- contaminated: {{ leakage.n_contaminated }} (fraction {{ leakage.fraction }})
{% for name, count in leakage.per_detector %}
- detector {{ name | md_escape }}: {{ count }}
{% endfor %}

## Provenance

- seed: {{ seed }}
{% for name, ver in pinned_versions %}
- {{ name | md_escape }} pinned: {{ ver | md_escape }}
{% endfor %}
{% for name, ver in runtime_versions %}
- {{ name | md_escape }} runtime: {{ ver | md_escape }}
{% endfor %}
{% if version_mismatches %}

**Version mismatch:** {{ version_mismatches | join(", ") | md_escape }}
{% endif %}

## Limitations

{% for lim in limitations %}
### {{ lim.title | md_escape }}

{{ lim.detail | md_escape }}

{% endfor %}
{% if stratification %}
## Stratified robustness

| axis | bucket | n | value | silent failure |
| --- | --- | --- | --- | --- |
{% for s in stratification %}
| {{ s.axis_name }} | {{ s.label }} | {{ s.n }} | {{ s.display }} | {{ s.silent_failure }} |
{% endfor %}
{% endif %}"""
)


def render_markdown(report: AuditReport) -> str:
    return _TEMPLATE.render(**build_context(report))
