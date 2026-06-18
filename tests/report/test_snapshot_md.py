"""(a) Markdown renderer: human-readable, deterministic, byte-stable against a golden."""

from __future__ import annotations

from tests.factories import make_audit_report
from tests.report import golden
from veritas.report import render_markdown


def test_markdown_has_headings_and_benchmark_name() -> None:
    md = render_markdown(make_audit_report())
    assert md.lstrip().startswith("#")  # a Markdown heading
    assert "demo-benchmark" in md


def test_markdown_is_deterministic() -> None:
    report = make_audit_report()
    assert render_markdown(report) == render_markdown(report)


def test_markdown_matches_committed_golden() -> None:
    assert render_markdown(make_audit_report()) == golden("report.md")


def test_md_escape_neutralizes_table_breakers() -> None:
    from veritas.report.numbers import md_escape

    assert md_escape("a|b") == "a\\|b"
    assert md_escape("x\ny") == "x y"
    assert md_escape("`code`") == "\\`code\\`"


def test_markdown_escapes_injected_user_text() -> None:
    # A benchmark name with a pipe and a newline must not corrupt the document.
    report = make_audit_report().model_copy(update={"benchmark_name": "evil|name\nrow2"})
    md = render_markdown(report)
    assert "evil\\|name row2" in md  # pipe escaped, newline folded to a space
    assert "\nrow2" not in md  # the injected newline did not start a new line
