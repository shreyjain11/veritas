"""(c) Provenance completeness: no number renders without its provenance ref.

TracedValue makes a number unforgeable at the type level (provenance_ref is
required); these tests assert the *renderers* surface that ref alongside every
value, in every format, and that the runtime-version manifest (req C) and any
pinned-vs-runtime mismatch are disclosed.
"""

from __future__ import annotations

import json

from tests.factories import make_audit_report
from veritas.report import render_html, render_json, render_markdown

_RENDERERS = (render_json, render_markdown, render_html)


def test_every_metric_number_is_accompanied_by_its_provenance_ref() -> None:
    report = make_audit_report()
    for render in _RENDERERS:
        out = render(report)
        for traced in (report.reported, report.honest, report.delta):
            assert traced.provenance_ref in out, (
                f"{render.__name__} dropped {traced.provenance_ref}"
            )


def test_json_structurally_pairs_each_value_with_a_ref() -> None:
    data = json.loads(render_json(make_audit_report()))
    for key in ("reported", "honest", "delta"):
        assert data[key]["provenance_ref"]  # present and non-empty
        assert "value" in data[key]


def test_manifest_discloses_runtime_versions() -> None:
    report = make_audit_report()
    for render in _RENDERERS:
        out = render(report)
        assert "mmseqs" in out
        assert "18.8cc5c" in out  # the runtime-captured version string


def test_pinned_vs_runtime_mismatch_is_flagged_not_dropped() -> None:
    report = make_audit_report(version_mismatch=True)
    assert report.provenance.version_mismatches == ("mmseqs",)
    data = json.loads(render_json(report))
    assert data["provenance"]["version_mismatches"] == ["mmseqs"]
    assert data["provenance"]["runtime_versions"]["mmseqs"] == "99.9.9"
    for render in (render_markdown, render_html):
        out = render(report).lower()
        assert "99.9.9" in out  # runtime version surfaced
        assert "mismatch" in out  # explicitly flagged


def test_no_false_mismatch_when_versions_agree() -> None:
    report = make_audit_report(version_mismatch=False)
    assert json.loads(render_json(report))["provenance"]["version_mismatches"] == []
    for render in (render_markdown, render_html):
        assert "mismatch" not in render(report).lower()
