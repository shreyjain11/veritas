"""(a) JSON renderer: machine-readable, deterministic, byte-stable against a golden.

The JSON form is the canonical machine artifact; it must parse, round-trip the
report's values, and match a committed golden byte-for-byte (canonical: sorted
keys, fixed float format) so any drift is caught.
"""

from __future__ import annotations

import json

from tests.factories import make_audit_report
from tests.report import golden
from veritas.report import render_json


def test_json_parses_and_carries_core_fields() -> None:
    data = json.loads(render_json(make_audit_report()))
    assert data["benchmark_name"] == "demo-benchmark"
    assert len(data["audit_hash"]) == 64  # sha256 hex, stamped by the assembler
    assert set(data) >= {"reported", "honest", "delta", "leakage", "provenance", "limitations"}


def test_json_is_deterministic() -> None:
    report = make_audit_report()
    assert render_json(report) == render_json(report)


def test_json_matches_committed_golden() -> None:
    # Golden generated and locked during GREEN; byte-identical canonical JSON.
    assert render_json(make_audit_report()) == golden("report.json")
