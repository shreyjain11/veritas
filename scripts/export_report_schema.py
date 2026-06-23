"""Export the AuditReport wire-format JSON Schema (the source of truth for the TS types).

Pydantic's model schema is the base; we then inject the three COMPUTED fields that
render_json emits but that are not model fields (so the schema matches the wire format,
not just the model): leakage.fraction_contaminated, provenance.version_mismatches, and
DetectorCell.rate. The schema feeds json-schema-to-typescript (web/lib/audit-report.ts)
and ajv validation of the committed fixtures.

Run:  uv run python scripts/export_report_schema.py
A test (tests/report/test_schema_export.py) fails if the committed schema drifts from a
fresh export, or if any fixture stops validating against it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from veritas.contracts import AuditReport

_OUT = Path(__file__).resolve().parents[1] / "schema" / "audit-report.schema.json"


def _inject(defs: dict[str, Any], name: str, prop: str, spec: dict[str, Any]) -> None:
    target = defs[name]
    target["properties"][prop] = spec
    # render_json always emits these computed fields when the parent object is present.
    target.setdefault("required", [])
    if prop not in target["required"]:
        target["required"].append(prop)
        target["required"].sort()


def build_schema() -> dict[str, Any]:
    schema = AuditReport.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "AuditReport"
    defs = schema["$defs"]
    _inject(defs, "LeakageSummary", "fraction_contaminated", {"type": "number"})
    _inject(defs, "DetectorCell", "rate", {"type": "number"})
    _inject(
        defs,
        "ProvenanceRecord",
        "version_mismatches",
        {"type": "array", "items": {"type": "string"}},
    )
    return schema


def main() -> None:
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(build_schema(), indent=2, sort_keys=True) + "\n"
    _OUT.write_text(text, encoding="utf-8")
    print(f"wrote {_OUT.relative_to(_OUT.parents[1])}")


if __name__ == "__main__":
    main()
