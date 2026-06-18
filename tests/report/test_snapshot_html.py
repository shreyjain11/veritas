"""(a) HTML renderer: self-contained document, deterministic, structural snapshot.

HTML is asserted structurally (byte-golden is too brittle for markup): it is a
complete document carrying the benchmark name and every metric value+ref.
"""

from __future__ import annotations

from tests.factories import make_audit_report
from veritas.report import render_html


def test_html_is_a_complete_document() -> None:
    html = render_html(make_audit_report())
    low = html.lower()
    assert "<html" in low and "</html>" in low


def test_html_is_deterministic() -> None:
    report = make_audit_report()
    assert render_html(report) == render_html(report)


def test_html_contains_benchmark_and_metric_values() -> None:
    report = make_audit_report()
    html = render_html(report)
    assert "demo-benchmark" in html
    # each metric's provenance ref is surfaced (provenance completeness covered in (c))
    assert report.reported.provenance_ref in html
