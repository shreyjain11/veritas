"""Python side of the type-safety gate: the exported JSON Schema is the wire contract.

(a) the committed schema equals a fresh export (no drift), and (b) render_json output for
every demo report validates against it — so the schema the TS types are generated from
genuinely describes what the serializer emits.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from veritas.demos.locked_reports import all_fixtures
from veritas.report import render_json

_REPO = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _REPO / "schema" / "audit-report.schema.json"


def _build_schema() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "export_report_schema", _REPO / "scripts" / "export_report_schema.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast("dict[str, Any]", module.build_schema())


def _schema() -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(_SCHEMA_PATH.read_text()))


def test_committed_schema_matches_fresh_export() -> None:
    fresh = json.dumps(_build_schema(), indent=2, sort_keys=True) + "\n"
    assert _SCHEMA_PATH.read_text() == fresh


def test_schema_itself_is_valid() -> None:
    Draft202012Validator.check_schema(_schema())


def test_render_json_validates_against_schema() -> None:
    validator = Draft202012Validator(_schema())
    for name, report in all_fixtures().items():
        data = json.loads(render_json(report))
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        assert not errors, f"{name}: {[(list(e.path), e.message) for e in errors[:3]]}"


def test_committed_fixtures_validate_against_schema() -> None:
    validator = Draft202012Validator(_schema())
    for path in sorted((_REPO / "web" / "fixtures").glob("*.json")):
        data = json.loads(path.read_text())
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        assert not errors, f"{path.name}: {[(list(e.path), e.message) for e in errors[:3]]}"
