"""(e) The report discloses known methodological limitations (a hashed field).

Two limitations must be surfaced so a reader is not misled:
  * bootstrap CI under-coverage at small n (measured ~0.927 at n=25) -- ALWAYS,
    because every CI in the report comes from the percentile bootstrap;
  * the MinHash/LSH prefilter's non-conservative recall -- ONLY when the
    prefilter was enabled for the audit.
Renderers read ``report.limitations`` (no limitations= argument).
"""

from __future__ import annotations

from tests.factories import make_audit_report
from veritas.report import collect_limitations, render_html, render_json, render_markdown

_RENDERERS = (render_json, render_markdown, render_html)


def test_collect_limitations_gates_on_prefilter() -> None:
    assert {lim.id for lim in collect_limitations(prefilter_enabled=True)} == {
        "bootstrap_small_n",
        "minhash_nonconservative",
    }
    assert {lim.id for lim in collect_limitations(prefilter_enabled=False)} == {"bootstrap_small_n"}


def test_bootstrap_under_coverage_is_always_disclosed_with_the_measured_figure() -> None:
    report = make_audit_report(prefilter_enabled=False)
    by_id = {lim.id: lim for lim in report.limitations}
    assert "bootstrap_small_n" in by_id
    detail = by_id["bootstrap_small_n"].detail
    assert "0.927" in detail and "25" in detail  # the specific measured under-coverage
    for render in _RENDERERS:
        assert "0.927" in render(report)


def test_minhash_disclosure_renders_only_when_prefilter_enabled() -> None:
    on = render_html(make_audit_report(prefilter_enabled=True))
    off = render_html(make_audit_report(prefilter_enabled=False))
    assert "non-conservative" in on.lower()
    assert "non-conservative" not in off.lower()
