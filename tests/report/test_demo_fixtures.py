"""Round-trip gate for the committed demo fixtures (req 2: serialization, not new science).

The committed web/fixtures/*.json must (a) equal a fresh render of veritas.demos.locked_reports
byte-for-byte (no drift), (b) carry the locked, e2e-validated numbers bit-for-bit, and (c)
hold a self-consistent audit_hash. Any divergence is an emission bug, not a science change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from veritas.demos.locked_reports import all_fixtures
from veritas.report import audit_hash_for, render_json

_FIXTURES = Path(__file__).resolve().parents[2] / "web" / "fixtures"


def _committed(name: str) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((_FIXTURES / f"{name}.json").read_text()))


@pytest.mark.parametrize("name", sorted(all_fixtures()))
def test_committed_fixture_matches_fresh_generation(name: str) -> None:
    # Drift guard: the file on disk is exactly what the generator emits today.
    expected = render_json(all_fixtures()[name])
    assert (_FIXTURES / f"{name}.json").read_text() == expected


@pytest.mark.parametrize("name", sorted(all_fixtures()))
def test_fixture_audit_hash_is_self_consistent(name: str) -> None:
    report = all_fixtures()[name]
    assert report.audit_hash == audit_hash_for(report)
    assert _committed(name)["audit_hash"] == report.audit_hash


@pytest.mark.parametrize("name", sorted(all_fixtures()))
def test_fixture_generation_is_deterministic(name: str) -> None:
    assert render_json(all_fixtures()[name]) == render_json(all_fixtures()[name])


# --- bit-for-bit locked numbers (the explicit round-trip requirement) ---------


def test_r2_reverse_complement_count_is_locked() -> None:
    cell = _committed("r2_reverse_complement")["splits"][0]["cells"][0]
    assert (cell["n_flagged"], cell["n_total"]) == (1616, 2000)


def test_proteingym_bucket_means_are_locked() -> None:
    strata = _committed("proteingym_msa_depth")["stratification"]
    assert [(s["bucket_label"], s["metric"]["value"]) for s in strata] == [
        ("Low", 0.298),
        ("Medium", 0.384),
        ("High", 0.531),
    ]


def test_ppi_matrix_counts_are_locked() -> None:
    splits = _committed("ppi_interface")["splits"]
    matrix = {
        s["split_name"]: {c["detector"]: (c["n_flagged"], c["n_total"]) for c in s["cells"]}
        for s in splits
    }
    assert matrix == {
        "demonstration (MMseqs2-30%)": {
            "sequence": (0, 52),
            "family": (18, 52),
            "structural": (20, 52),
        },
        "Pr/PI control (published)": {
            "sequence": (0, 60),
            "family": (0, 60),
            "structural": (2, 60),
        },
        "AB/AG hold-out": {"sequence": (48, 53), "family": (52, 53), "structural": (51, 53)},
        "TCR/pMHC hold-out": {"sequence": (33, 38), "family": (38, 38), "structural": (38, 38)},
    }


def test_r3_metric_numbers_are_locked() -> None:
    random = _committed("r3_random")
    assert (random["reported"]["value"], random["honest"]["value"], random["delta"]["value"]) == (
        0.165,
        0.018,
        0.147,
    )
    assert random["leakage"]["n_contaminated"] == 1230
    chr_holdout = _committed("r3_chr8_chr9")
    assert (
        chr_holdout["reported"]["value"],
        chr_holdout["honest"]["value"],
        chr_holdout["delta"]["value"],
    ) == (0.074, 0.030, 0.044)
    assert chr_holdout["leakage"]["n_contaminated"] == 828
