"""(c/req B) Non-OK statuses render as explicit, readable states -- never NaN/blank.

When a metric is insufficient_clean_data or undefined_metric, JSON carries an
explicit null + status (no NaN literal) and the prose formats spell the status out.
"""

from __future__ import annotations

import json

from tests.factories import make_audit_report
from veritas.contracts import ResultStatus
from veritas.report import render_html, render_json, render_markdown


def test_insufficient_clean_data_renders_explicitly() -> None:
    report = make_audit_report(
        honest_status=ResultStatus.INSUFFICIENT_CLEAN_DATA,
        delta_status=ResultStatus.INSUFFICIENT_CLEAN_DATA,
    )
    data = json.loads(render_json(report))
    assert data["honest"]["value"] is None  # explicit null, not NaN
    assert data["honest"]["status"] == "insufficient_clean_data"
    assert "NaN" not in render_json(report)  # json's nan literal never emitted
    for render in (render_markdown, render_html):
        out = render(report)
        assert "insufficient clean data" in out  # spelled out, not blank
        assert "NaN" not in out


def test_undefined_metric_renders_explicitly() -> None:
    report = make_audit_report(
        reported_status=ResultStatus.UNDEFINED_METRIC,
        honest_status=ResultStatus.UNDEFINED_METRIC,
        delta_status=ResultStatus.UNDEFINED_METRIC,
    )
    data = json.loads(render_json(report))
    assert data["reported"]["value"] is None
    assert data["reported"]["status"] == "undefined_metric"
    for render in (render_markdown, render_html):
        out = render(report)
        assert "undefined metric" in out
        assert "NaN" not in out
