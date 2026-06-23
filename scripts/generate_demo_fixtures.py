"""Write the five locked demo AuditReport fixtures to web/fixtures/ (the viewer's data).

Pure serialization of veritas.demos.locked_reports (already-validated results). Run:

    uv run python scripts/generate_demo_fixtures.py

tests/report/test_demo_fixtures.py re-runs this in memory and fails if the committed
files drift, so the fixtures cannot go stale.
"""

from __future__ import annotations

from pathlib import Path

from veritas.demos.locked_reports import all_fixtures
from veritas.report import render_json

_OUT = Path(__file__).resolve().parents[1] / "web" / "fixtures"


def main() -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    for name, report in all_fixtures().items():
        path = _OUT / f"{name}.json"
        path.write_text(render_json(report), encoding="utf-8")
        print(f"wrote {path.relative_to(_OUT.parents[1])}  ({report.report_kind.value})")


if __name__ == "__main__":
    main()
