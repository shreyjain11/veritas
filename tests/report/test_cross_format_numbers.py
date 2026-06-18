"""(b) Cross-format number agreement: no rounding drift between HTML/JSON/MD.

The same computed value must render to the SAME bytes in all three formats and
equal the canonical formatting of the computed value. A value with a long
binary-float tail (0.1 + 0.2 == 0.30000000000000004) makes any per-format
rounding visible as a substring mismatch.
"""

from __future__ import annotations

import json

from tests.factories import make_audit_report
from veritas.report import format_number, render_html, render_json, render_markdown

_DRIFTY = 0.1 + 0.2  # 0.30000000000000004


def test_formatter_does_not_round() -> None:
    assert format_number(_DRIFTY) == "0.30000000000000004"


def test_same_value_is_byte_identical_in_all_three_formats() -> None:
    report = make_audit_report(reported_value=_DRIFTY)
    value = report.reported.value
    assert value is not None
    token = format_number(value)
    for fmt, out in (
        ("json", render_json(report)),
        ("markdown", render_markdown(report)),
        ("html", render_html(report)),
    ):
        assert token in out, f"{fmt} dropped/rounded the value (expected exact {token!r})"


def test_json_value_matches_the_canonical_formatting() -> None:
    report = make_audit_report(reported_value=_DRIFTY)
    value = report.reported.value
    assert value is not None
    data = json.loads(render_json(report))
    assert format_number(data["reported"]["value"]) == format_number(value)
