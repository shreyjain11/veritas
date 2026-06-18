"""(d) HTML self-containment: no external resources (inline CSS + inline SVG only).

A report must render identically offline with no network: no external scripts,
stylesheets, or http(s) ``src`` references / CDNs. (SVG xmlns URIs are namespace
identifiers, not fetched resources, so they are checked via src/href only.)
"""

from __future__ import annotations

from tests.factories import make_audit_report
from veritas.report import render_html


def test_html_has_no_external_resources() -> None:
    html = render_html(make_audit_report())
    low = html.lower()
    assert "<script" not in low  # no JS at all
    assert "<link" not in low  # no external stylesheet
    assert 'src="http' not in low and "src='http" not in low
    assert "cdn" not in low
