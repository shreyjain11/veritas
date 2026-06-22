"""(a) The pipeline steps are independently callable and compose into run_audit.

``detect`` / ``rescore`` / ``stratify`` are the reusable stages the CLI subcommands
call; run_audit chains them. Each is exercised in isolation, then checked for
consistency with the full run.
"""

from __future__ import annotations

import pytest

from tests.factories import AuditCase, make_golden_audit
from veritas.audit import detect, rescore, run_audit, stratify
from veritas.contamination.graph import contaminated_eval_ids
from veritas.contracts import AuditInputs, ContaminationGraph


def test_detect_returns_a_contamination_graph() -> None:
    case = make_golden_audit()
    graph = detect(case.config, case.inputs, detector_factory=case.detector_factory)
    assert isinstance(graph, ContaminationGraph)
    assert len(contaminated_eval_ids(graph)) == 10  # the planted contaminated items


def test_rescore_computes_honest_metrics_from_a_graph() -> None:
    case = make_golden_audit()
    graph = detect(case.config, case.inputs, detector_factory=case.detector_factory)
    comparison = rescore(case.config, case.inputs, graph)
    assert comparison.reported.value == pytest.approx(case.expected_reported)
    assert comparison.honest.value == pytest.approx(case.expected_honest)
    assert comparison.delta.value == pytest.approx(case.expected_delta)


def test_stratify_returns_one_curve_per_configured_axis() -> None:
    case = make_golden_audit()
    graph = detect(case.config, case.inputs, detector_factory=case.detector_factory)
    curves = stratify(case.config, case.inputs, graph)
    assert len(curves) == len(case.config.stratify_axes) == 1
    assert curves[0].buckets  # bucketed on the identity axis


def test_stratify_supports_the_label_class_axis() -> None:
    case = make_golden_audit()
    config = case.config.model_copy(update={"stratify_axes": ("label_class",)})
    graph = detect(config, case.inputs, detector_factory=case.detector_factory)
    curves = stratify(config, case.inputs, graph)
    assert curves[0].axis_name == "label_class"


def test_stratify_rejects_an_unknown_axis() -> None:
    case = make_golden_audit()
    config = case.config.model_copy(update={"stratify_axes": ("bogus_axis",)})
    graph = detect(config, case.inputs, detector_factory=case.detector_factory)
    with pytest.raises(ValueError, match="unknown stratification axis"):
        stratify(config, case.inputs, graph)


def _tagged_inputs(case: AuditCase, depths: tuple[str, ...]) -> AuditInputs:
    # Tag each eval item with a categorical metadata field so a metadata axis can bucket it.
    tagged = tuple(
        item.model_copy(update={"metadata": {"depth": depths[i % len(depths)]}})
        for i, item in enumerate(case.inputs.benchmark.eval_items)
    )
    benchmark = case.inputs.benchmark.model_copy(update={"eval_items": tagged})
    return case.inputs.model_copy(update={"benchmark": benchmark})


def test_stratify_supports_a_metadata_category_axis() -> None:
    case = make_golden_audit()
    inputs = _tagged_inputs(case, ("Low", "High"))
    config = case.config.model_copy(update={"stratify_axes": ("metadata:depth",)})
    graph = detect(config, inputs, detector_factory=case.detector_factory)
    curves = stratify(config, inputs, graph)
    assert curves[0].axis_name == "metadata:depth"
    assert {b.label for b in curves[0].buckets} == {"Low", "High"}


def test_metadata_axis_labels_strata_with_category_names() -> None:
    case = make_golden_audit()
    inputs = _tagged_inputs(case, ("Low", "High"))
    config = case.config.model_copy(update={"stratify_axes": ("metadata:depth",)})
    report = run_audit(config, inputs, detector_factory=case.detector_factory)
    labels = {s.bucket_label for s in report.stratification}
    assert labels == {"Low", "High"}  # category names, not "[lo, hi)" ranges


def test_metadata_axis_requires_a_key() -> None:
    case = make_golden_audit()
    config = case.config.model_copy(update={"stratify_axes": ("metadata:",)})
    graph = detect(config, case.inputs, detector_factory=case.detector_factory)
    with pytest.raises(ValueError, match="needs a key"):
        stratify(config, case.inputs, graph)


def test_steps_agree_with_the_full_run() -> None:
    case = make_golden_audit()
    report = run_audit(
        case.config,
        case.inputs,
        detector_factory=case.detector_factory,
        version_runner=case.version_runner,
    )
    graph = detect(case.config, case.inputs, detector_factory=case.detector_factory)
    comparison = rescore(case.config, case.inputs, graph)
    assert report.reported.value == comparison.reported.value
    assert report.honest.value == comparison.honest.value
