"""Option B: detection + stratification report kinds — assembly, hashing, rendering, guards.

These exercise the wire-format extension end to end: the new assemblers stamp a matching
audit_hash; report_kind + the splits-matrix enter the hashed content; render_json emits the
new shape (null metric slots, splits with a derived rate); and the Markdown/HTML renderers
refuse a non-metric report rather than crashing on a null slot.
"""

from __future__ import annotations

import json

import pytest

from veritas.contracts import (
    AuditReport,
    DetectorCell,
    LeakageSplit,
    Limitation,
    ProvenanceRecord,
    ReportKind,
    SplitRole,
    StratumResult,
    TracedValue,
)
from veritas.report import (
    assemble_detection_report,
    assemble_stratification_report,
    audit_hash_for,
    render_html,
    render_json,
    render_markdown,
)


def _prov() -> ProvenanceRecord:
    return ProvenanceRecord(
        input_hashes={"benchmark": "sha256:abc"},
        params={},
        seed=1729,
        pinned_versions={"foldseek": "10.941cd33"},
    )


def _split(fam: int = 18) -> LeakageSplit:
    return LeakageSplit(
        split_name="demonstration",
        role=SplitRole.DEMONSTRATION,
        cells=(
            DetectorCell(detector="sequence", n_flagged=0, n_total=52, threshold_label="id>=0.30"),
            DetectorCell(
                detector="family", n_flagged=fam, n_total=52, threshold_label="Pfam e<=1e-3"
            ),
            DetectorCell(
                detector="structural", n_flagged=20, n_total=52, threshold_label="TM>=0.50"
            ),
        ),
    )


def _detection() -> AuditReport:
    return assemble_detection_report(
        benchmark_name="ppi",
        splits=(_split(),),
        provenance=_prov(),
        limitations=(
            Limitation(
                id="foldseek_fold_level", title="Fold-level, not interface-level", detail="…"
            ),
        ),
    )


def _stratification() -> AuditReport:
    strata = tuple(
        StratumResult(
            axis_name="metadata:MSA_Neff_L_category",
            bucket_index=i,
            bucket_label=label,
            n=15,
            metric=TracedValue(name="spearman", value=value, provenance_ref=f"prov:{label}"),
        )
        for i, (label, value) in enumerate([("Low", 0.298), ("Medium", 0.384), ("High", 0.531)])
    )
    return assemble_stratification_report(
        benchmark_name="proteingym", stratification=strata, provenance=_prov()
    )


def test_detection_report_assembles_with_matching_hash() -> None:
    report = _detection()
    assert report.report_kind is ReportKind.DETECTION
    assert report.audit_hash == audit_hash_for(report)
    assert report.reported is None and report.leakage is None


def test_stratification_report_assembles_with_matching_hash() -> None:
    report = _stratification()
    assert report.report_kind is ReportKind.STRATIFICATION
    assert report.audit_hash == audit_hash_for(report)


def test_render_json_detection_shape() -> None:
    data = json.loads(render_json(_detection()))
    assert data["report_kind"] == "detection"
    assert data["reported"] is None and data["leakage"] is None
    cell = data["splits"][0]["cells"][1]
    assert cell["detector"] == "family" and cell["n_flagged"] == 18 and cell["n_total"] == 52
    assert cell["rate"] == pytest.approx(18 / 52)
    assert cell["threshold_label"] == "Pfam e<=1e-3"


def test_render_json_stratification_shape() -> None:
    data = json.loads(render_json(_stratification()))
    assert data["report_kind"] == "stratification"
    assert data["reported"] is None
    assert [s["metric"]["value"] for s in data["stratification"]] == [0.298, 0.384, 0.531]


def test_report_kind_is_in_hashed_content() -> None:
    from veritas.report.model import _hashable_content

    assert _hashable_content(_detection())["report_kind"] == "detection"


def test_changing_a_cell_count_changes_the_hash() -> None:
    base = _detection()
    bumped = base.model_copy(update={"splits": (_split(fam=19),)})
    assert audit_hash_for(bumped) != audit_hash_for(base)


def test_markdown_and_html_reject_non_metric_reports() -> None:
    for render in (render_markdown, render_html):
        with pytest.raises(ValueError, match="metric_audit"):
            render(_detection())
