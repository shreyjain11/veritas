"""The bundled web sample report is a real, reproducible pipeline output with a valid hash."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from veritas.benchmark_integrity.contracts import AuditReport
from veritas.benchmark_integrity.hashing import verify_report_hash

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "web" / "fixtures" / "v2_sample_report.json"


def test_sample_report_is_valid_and_hash_verified() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    AuditReport.model_validate(data)
    assert verify_report_hash(data)[0] is True
    assert data["provenance"]["model"]["id"] == "synthetic-replay-fixture"


def test_sample_report_regenerates_byte_identically(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "generate_v2_sample_report", ROOT / "scripts" / "generate_v2_sample_report.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.chdir(ROOT)
    assert module.build() == FIXTURE.read_text(encoding="utf-8"), (
        "web/fixtures/v2_sample_report.json is stale: run "
        "`uv run python scripts/generate_v2_sample_report.py`"
    )
