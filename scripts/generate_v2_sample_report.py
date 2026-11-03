"""Generate the bundled schema-v2 sample report used by the web viewer.

The report is produced by the real audit pipeline from a *synthetic* benchmark and a
*synthetic* replay "model" whose answers are scripted to show what each verdict looks
like (it tracks content on most items but follows the original answer position on a
few). It demonstrates the viewer and doubles as a cross-language fixture: the web test
suite re-derives its audit_hash in TypeScript. It is not a measurement of any model.

    uv run python scripts/generate_v2_sample_report.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from veritas.benchmark_integrity.contracts import AuditSpec, BenchmarkItem, Choice, TaskType
from veritas.benchmark_integrity.reporting import render_json
from veritas.benchmark_integrity.service import audit
from veritas.benchmark_integrity.transforms import generate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "fixtures" / "v2" / "sample_report.json"
SEED = 42
N_ITEMS = 40
# Items where the scripted model follows the original answer *letter* instead of content.
POSITION_BOUND = {2, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 38}
CANONICAL_MISSES = {9}
TEMPLATE_MISSES = {4}


def _items() -> list[BenchmarkItem]:
    items = []
    for index in range(N_ITEMS):
        a, b = 7 + 3 * index, 4 + 5 * index
        total = a + b
        options = [total, total + 1, total - 2, total + 10]
        rotation = index % 4
        options = options[rotation:] + options[:rotation]
        labels = "abcd"
        items.append(
            BenchmarkItem(
                id=f"add-{index:02d}",
                prompt=f"What is {a} + {b}?",
                expected_output=labels[options.index(total)],
                task_type=TaskType.MULTIPLE_CHOICE,
                choices=tuple(
                    Choice(id=label, text=str(value))
                    for label, value in zip(labels, options, strict=True)
                ),
                family_id="arithmetic",
                metadata={"synthetic": True},
            )
        )
    return items


def _responses(items: list[BenchmarkItem]) -> dict[str, object]:
    responses: dict[str, object] = {}
    for index, item in enumerate(items):
        wrong = next(c.id for c in item.choices or () if c.id != item.expected_output)
        responses[item.id] = (
            f"The answer is {wrong}" if index in CANONICAL_MISSES else str(item.expected_output)
        )
    for family in ("choice_permutation", "choice_label_remap", "formatting"):
        for derived in generate(items, family, 1, SEED):
            parent = int(derived.transformation.parent_item_id.split("-")[1])
            answer = str(derived.item.expected_output)
            if family == "choice_permutation" and parent in POSITION_BOUND:
                # A position-bound model repeats the canonical label, now pointing elsewhere.
                answer = str(items[parent].expected_output)
            if family == "choice_label_remap" and parent in POSITION_BOUND:
                # ...and still answers with the old letter once the labels are renamed.
                answer = f"The answer is {items[parent].expected_output}"
            if family == "formatting" and parent in TEMPLATE_MISSES:
                answer = "I'm not sure."
            responses[derived.item.id] = answer
    return responses


def build() -> str:
    """Run the real pipeline from the repo root (relative paths keep it byte-reproducible)."""
    items = _items()
    benchmark_path = Path("web/fixtures/v2/.sample_items.jsonl")
    benchmark_path.write_text(
        "".join(item.model_dump_json() + "\n" for item in items), encoding="utf-8"
    )
    try:
        spec = AuditSpec.model_validate(
            {
                "benchmark": {
                    "adapter": "jsonl",
                    "id": "synthetic-arithmetic-demo",
                    "version": "1",
                    "path": str(benchmark_path),
                    "visibility": "public",
                },
                "model": {
                    "id": "synthetic-replay-fixture",
                    "adapter": "replay",
                    "generation": {"extra": {"responses": _responses(items)}},
                },
                "transformations": [
                    {"type": "choice_permutation"},
                    {"type": "choice_label_remap"},
                    {"type": "formatting"},
                ],
                "detectors": [
                    {"type": "perturbation"},
                    {"type": "option_order"},
                    {"type": "template_dependence"},
                    {"type": "exact_match"},
                    {"type": "probability"},
                    {"type": "fresh_set"},
                ],
                "runtime": {"seed": SEED},
                "report": {"reported_score": 0.98},
            }
        )
        report = audit(spec)
    finally:
        benchmark_path.unlink(missing_ok=True)
    return render_json(report)


def main() -> int:
    os.chdir(ROOT)
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
