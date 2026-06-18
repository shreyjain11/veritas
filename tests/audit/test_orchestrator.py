"""(a) The orchestrator: config -> contamination -> de-leak -> honest -> stratify -> report.

run_audit is the single source of truth (CLAUDE.md / PLAN §8). It runs the whole
pipeline and returns a fully-assembled AuditReport. The cornerstone test is the
req-C wiring: every MetricEstimate produced inside the pipeline leaves as a
TracedValue whose provenance_ref resolves to the run's ProvenanceRecord -- a number
cannot escape the orchestrator un-stamped.
"""

from __future__ import annotations

import pytest

from tests.factories import AuditCase, PlantedDetector, make_golden_audit, planted_factory
from veritas.audit import run_audit
from veritas.contamination.base import ContaminationDetector
from veritas.contracts import (
    AuditReport,
    ContaminationEdge,
    ContaminationGraph,
    DetectorKind,
    ResultStatus,
)
from veritas.provenance import audit_hash
from veritas.report import render_html, render_markdown


def _run(*, stratify: bool = True, version: str = "18.8cc5c") -> tuple[AuditCase, AuditReport]:
    case = make_golden_audit(stratify=stratify, version=version)
    report = run_audit(
        case.config,
        case.inputs,
        detector_factory=case.detector_factory,
        version_runner=case.version_runner,
    )
    return case, report


def test_run_audit_returns_a_fully_assembled_report() -> None:
    _case, report = _run()
    assert isinstance(report, AuditReport)
    assert report.benchmark_name == "golden"
    assert len(report.audit_hash) == 64  # stamped over the assembled content
    assert report.status is ResultStatus.OK
    # limitations are collected during assembly (prefilter caveat etc.)
    assert any(lim.id == "bootstrap_small_n" for lim in report.limitations)


def test_pipeline_recovers_the_planted_metric_gap() -> None:
    case, report = _run()
    assert report.reported.value == pytest.approx(case.expected_reported)  # 0.8
    assert report.honest.value == pytest.approx(case.expected_honest)  # 0.6
    assert report.delta.value == pytest.approx(case.expected_delta)  # 0.2 (float subtraction)
    assert report.leakage.n_contaminated == 10  # the planted contaminated items


def test_every_metric_is_a_traced_value_with_a_real_provenance_ref() -> None:
    _case, report = _run()
    provenance_ref = audit_hash(report.provenance)  # the run's provenance content id
    for traced in (report.reported, report.honest, report.delta):
        assert traced.provenance_ref  # never empty
        # resolves to THIS run's provenance, not a placeholder string
        assert traced.provenance_ref == provenance_ref


def test_stratification_is_included_and_its_numbers_are_traced() -> None:
    _case, report = _run(stratify=True)
    assert report.stratification  # populated for the configured axis
    provenance_ref = audit_hash(report.provenance)
    for stratum in report.stratification:
        assert stratum.axis_name == "identity_to_nearest_reference"
        if stratum.metric.status is ResultStatus.OK:
            assert stratum.metric.provenance_ref == provenance_ref


def test_no_stratification_section_when_no_axes_configured() -> None:
    _case, report = _run(stratify=False)
    assert report.stratification == ()


def test_leakage_count_ignores_graph_ids_absent_from_the_benchmark() -> None:
    # A precomputed graph may name ids the benchmark lacks; those are not de-leaked,
    # so n_contaminated must count only contaminated *eval* items (the planted 10).
    case = make_golden_audit()
    planted = case.detector_factory("planted").detect(
        case.inputs.benchmark.eval_items, case.inputs.reference_items, case.config.detectors[0]
    )
    orphan = ContaminationEdge(
        eval_id="ghost-not-in-benchmark",
        ref_id="r",
        score=1.0,
        kind=DetectorKind.SEQUENCE,
        detector_id="planted",
    )
    polluted = ContaminationGraph(edges=(*planted.edges, orphan))
    report = run_audit(
        case.config,
        case.inputs,
        detector_factory=planted_factory(polluted),
        version_runner=case.version_runner,
    )
    assert report.leakage.n_contaminated == 10


def test_resolved_binary_path_is_recorded_in_provenance() -> None:
    # Security/provenance: the absolute binary each detector resolved is stamped into
    # the manifest, so the report records exactly which binary ran.
    case = make_golden_audit()
    planted = case.detector_factory("planted").detect(
        case.inputs.benchmark.eval_items, case.inputs.reference_items, case.config.detectors[0]
    )
    pinned_path = "/opt/veritas/bin/planted-mmseqs"

    def factory(name: str) -> ContaminationDetector:
        return PlantedDetector(planted, name, binary_path=pinned_path)

    report = run_audit(
        case.config,
        case.inputs,
        detector_factory=factory,
        version_runner=case.version_runner,
    )
    assert report.provenance.params["resolved_binaries"]["planted"] == pinned_path


def test_runtime_versions_are_captured_through_the_injected_runner() -> None:
    # req C: backend versions are captured at run time. The injected runner keeps it
    # hermetic; its output must actually reach the provenance record.
    _case, report = _run(version="X-CUSTOM-VER")
    assert report.provenance.runtime_versions  # non-empty
    assert "X-CUSTOM-VER" in report.provenance.runtime_versions.values()


def test_declared_pin_vs_runtime_mismatch_is_surfaced_and_rendered() -> None:
    # Decision 3: pinned comes from the declared config, not from probing the binary.
    # A runtime version differing from the declared pin must surface as a mismatch
    # AND be rendered in the report.
    _case, report = _run(version="0.0.0-drifted")  # != declared pin "18.8cc5c"
    assert report.provenance.version_mismatches == ("planted",)
    for render in (render_markdown, render_html):
        assert "mismatch" in render(report).lower()


def test_no_mismatch_when_runtime_matches_the_declared_pin() -> None:
    _case, report = _run(version="18.8cc5c")  # == declared pin
    assert report.provenance.version_mismatches == ()
