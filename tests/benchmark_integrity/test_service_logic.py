"""Regression tests for the v2 decision logic: pairing, verdicts, matrix, and hashing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from veritas.audit.gate import evaluate_gate
from veritas.benchmark_integrity.contracts import (
    AuditReport,
    AuditSpec,
    EvidenceDirection,
    EvidenceStrength,
    FindingStatus,
)
from veritas.benchmark_integrity.hashing import (
    canonical_json,
    canonicalize,
    report_hash,
    verify_report_hash,
)
from veritas.benchmark_integrity.service import audit, inspect_audit, load_spec
from veritas.benchmark_integrity.transforms import generate


def _items(path: Path, n: int) -> Path:
    rows = [
        {
            "id": f"q{index}",
            "prompt": f"Question {index}?",
            "expected_output": "a",
            "choices": [
                {"id": "a", "text": f"right {index}"},
                {"id": "b", "text": f"wrong {index}"},
            ],
        }
        for index in range(n)
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _spec(
    tmp_path: Path,
    *,
    n: int = 12,
    variants_correct: bool | None = True,
    detectors: tuple[str, ...] = ("perturbation", "option_order"),
    transformations: tuple[str, ...] = ("choice_permutation",),
    **extra: Any,
) -> AuditSpec:
    items = _items(tmp_path / "items.jsonl", n)
    responses: dict[str, object] = {f"q{index}": "a" for index in range(n)}
    # The permuted variant moves each item's answer to label b.
    if variants_correct is not None:
        for index in range(n):
            responses[f"q{index}::choice-order::42"] = "b" if variants_correct else "a"
    raw: dict[str, Any] = {
        "benchmark": {"adapter": "jsonl", "path": str(items)},
        "model": {
            "id": "fixture",
            "adapter": "replay",
            "generation": {"extra": {"responses": responses}},
        },
        "transformations": [{"type": name} for name in transformations],
        "detectors": [{"type": name} for name in detectors],
        "runtime": {"seed": 42},
    }
    raw.update(extra)
    return AuditSpec.model_validate(raw)


def _finding(report: AuditReport, detector: str) -> Any:
    return next(f for f in report.findings if f.detector_id == detector)


def test_audit_without_transformations_does_not_crash(tmp_path: Path) -> None:
    report = audit(_spec(tmp_path, transformations=(), detectors=("probability",)))
    assert [f.detector_id for f in report.findings] == ["probability"]
    assert report.score.robust_score is None


def test_each_detector_reports_exactly_once(tmp_path: Path) -> None:
    report = audit(_spec(tmp_path, detectors=("perturbation", "option_order", "perturbation")))
    ids = [f.detector_id for f in report.findings]
    assert ids == ["perturbation", "option_order"]


def test_robust_model_yields_evidence_against_dependence(tmp_path: Path) -> None:
    report = audit(_spec(tmp_path, variants_correct=True))
    assert report.score.canonical_reproduced_score == 1.0
    assert report.score.robust_score == 1.0
    assert report.score.robustness_gap == 0.0
    finding = _finding(report, "option_order")
    assert finding.direction is EvidenceDirection.CONTRADICTS
    assert finding.strength is EvidenceStrength.AGAINST
    row = next(r for r in report.evidence_matrix if r.hypothesis == "answer-position dependence")
    assert row.contradicting == ("option_order",)
    assert row.confidence is EvidenceStrength.AGAINST


def test_position_bound_model_yields_supporting_evidence(tmp_path: Path) -> None:
    report = audit(_spec(tmp_path, variants_correct=False))
    assert report.score.robustness_gap == 1.0
    finding = _finding(report, "option_order")
    assert finding.direction is EvidenceDirection.SUPPORTS
    assert finding.strength is EvidenceStrength.WEAK_INDIRECT
    assert finding.corrected_p_value is not None and finding.corrected_p_value <= 0.05
    assert finding.details["mcnemar"]["canonical_only"] == 12
    row = next(r for r in report.evidence_matrix if r.hypothesis == "answer-position dependence")
    assert row.supporting == ("option_order",)
    assert row.confidence is EvidenceStrength.WEAK_INDIRECT


def test_small_samples_stay_inconclusive(tmp_path: Path) -> None:
    report = audit(_spec(tmp_path, n=4, variants_correct=False))
    finding = _finding(report, "option_order")
    assert finding.direction is EvidenceDirection.INCONCLUSIVE
    assert "fewer than 10" in finding.details["decision_rule"]
    assert any("paired item" in note for note in report.limitations)


def test_decision_thresholds_are_configurable(tmp_path: Path) -> None:
    spec = _spec(tmp_path, n=4, variants_correct=False)
    spec = spec.model_copy(
        update={
            "detectors": (
                spec.detectors[0],
                spec.detectors[1].model_copy(update={"config": {"min_parent_items": 2}}),
            )
        }
    )
    finding = _finding(audit(spec), "option_order")
    # 4 pairs cannot reach p <= 0.05 with a sign-flip test, so the verdict is still honest.
    assert finding.direction is EvidenceDirection.INCONCLUSIVE
    assert "interval" in finding.details["decision_rule"]


def test_missing_responses_are_excluded_not_scored_wrong(tmp_path: Path) -> None:
    report = audit(_spec(tmp_path, variants_correct=None))
    assert report.score.canonical_reproduced_score == 1.0
    assert report.score.robust_score is None
    finding = _finding(report, "option_order")
    assert finding.status is FindingStatus.NOT_RUN
    assert finding.details["errored_variant_count"] == 12
    assert any("excluded from paired comparisons" in note for note in report.limitations)


def test_gap_is_computed_on_paired_items_only(tmp_path: Path) -> None:
    spec = _spec(tmp_path, variants_correct=True)
    responses = dict(spec.model.generation.extra["responses"])
    responses["q0"] = "b"  # one canonical miss
    for index in range(1, 12):  # variants exist only for items 1..11
        responses[f"q{index}::choice-order::42"] = "b"
    del responses["q0::choice-order::42"]
    model = spec.model.model_copy(
        update={
            "generation": spec.model.generation.model_copy(
                update={"extra": {"responses": responses}}
            )
        }
    )
    report = audit(spec.model_copy(update={"model": model}))
    assert report.score.canonical_reproduced_score == pytest.approx(11 / 12)
    # The unpaired miss on q0 must not leak into the robustness gap.
    assert report.score.robustness_gap == 0.0


def test_exact_match_without_reference_corpus_is_not_run(tmp_path: Path) -> None:
    report = audit(_spec(tmp_path, detectors=("exact_match",)))
    assert _finding(report, "exact_match").status is FindingStatus.NOT_RUN


def test_exact_match_normalizes_whitespace_and_case(tmp_path: Path) -> None:
    spec = _spec(
        tmp_path,
        detectors=("exact_match",),
        runtime={"seed": 42, "reference_texts": ["  question 3? "]},
    )
    finding = _finding(audit(spec), "exact_match")
    assert finding.item_ids == ("q3",)
    assert finding.strength is EvidenceStrength.DIRECT


def test_unknown_detectors_and_transforms_fail_before_any_request(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown detector"):
        inspect_audit(_spec(tmp_path, detectors=("perturbaton",)))
    with pytest.raises(ValueError, match="unknown transformation"):
        audit(_spec(tmp_path, transformations=("paraphrase",)))


def test_reported_score_and_matrix_rows_are_explicit(tmp_path: Path) -> None:
    report = audit(_spec(tmp_path, report={"reported_score": 0.9}))
    assert report.score.reported_score == 0.9
    fresh = next(r for r in report.evidence_matrix if r.hypothesis == "fresh-set generalization")
    assert fresh.unavailable == ("fresh_set",)
    assert fresh.confidence is EvidenceStrength.UNAVAILABLE


def test_perturbation_reports_family_breakdown_including_unvalidated(tmp_path: Path) -> None:
    items = tmp_path / "algebra.jsonl"
    items.write_text(
        json.dumps(
            {
                "id": "alg",
                "prompt": "If x = 2, what is x + 1?",
                "expected_output": "a",
                "choices": [{"id": "a", "text": "3"}, {"id": "b", "text": "4"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    spec = _spec(tmp_path, transformations=("choice_permutation", "identifier"))
    benchmark = {**spec.benchmark, "path": str(items)}
    responses = {"alg": "a", "alg::choice-order::42": "b", "alg::identifier::42": "a"}
    model = spec.model.model_copy(
        update={
            "generation": spec.model.generation.model_copy(
                update={"extra": {"responses": responses}}
            )
        }
    )
    report = audit(spec.model_copy(update={"benchmark": benchmark, "model": model}))
    families = _finding(report, "perturbation").details["families"]
    assert families["choice_permutation"]["included_in_robust_score"] is True
    assert families["identifier"]["included_in_robust_score"] is False
    assert families["identifier"]["validation"] == "unvalidated"


def test_external_scoring_does_not_fabricate_accuracy(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    benchmark = {**spec.benchmark, "scoring": {"kind": "external_code_grader_required"}}
    report = audit(spec.model_copy(update={"benchmark": benchmark}))
    assert report.score.canonical_reproduced_score is None
    assert _finding(report, "option_order").status is FindingStatus.NOT_RUN


def test_audit_hash_covers_the_whole_report(tmp_path: Path) -> None:
    report = audit(_spec(tmp_path))
    data = json.loads(report.model_dump_json())
    assert verify_report_hash(data)[0] is True
    for path in (("score", "robust_score"), ("responses", 13, "raw_text"), ("limitations", 0)):
        tampered = json.loads(report.model_dump_json())
        target = tampered
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = "edited" if isinstance(target[path[-1]], str) else 0.123
        assert verify_report_hash(tampered)[0] is False, path


def test_hash_canonicalization_is_cross_language_stable() -> None:
    assert canonicalize({"a": 1.0, "b": [2.5, -0.0, True, None]}) == {
        "a": 1,
        "b": [2.5, 0, True, None],
    }
    assert canonical_json({"b": 1e-07, "a": "é"}) == '{"a":"\\u00e9","b":1e-07}'
    # Shared vector, pinned identically in web/test/v2-hash.test.ts: the browser must
    # reproduce Python's canonical form (int-valued floats as ints, repr exponents).
    vector = {
        "audit_hash": "ignored",
        "x": 0.1,
        "y": 3.0,
        "z": "é",
        "p": 1e-07,
        "big": 1e16,
        "n": [1.5e300, -2.5e-12],
    }
    assert report_hash(vector) == "7fea7cae1e900571941817cf84637d69a6561e501710fa109721bb6ca62292ba"
    with pytest.raises(ValueError, match="non-finite"):
        canonicalize(float("nan"))


def test_gate_supports_v2_reports(tmp_path: Path) -> None:
    data = json.loads(audit(_spec(tmp_path, variants_correct=False)).model_dump_json())
    passed, message = evaluate_gate(data, 0.05)
    assert passed is False and "robustness gap" in message
    data["score"]["robustness_gap"] = 0.01
    assert evaluate_gate(data, 0.05)[0] is True
    data["score"]["robustness_gap"] = None
    assert evaluate_gate(data, 0.05)[0] is False


def test_load_spec_resolves_benchmark_path_beside_the_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _items(tmp_path / "items.jsonl", 2)
    (tmp_path / "audit.json").write_text(
        json.dumps(
            {
                "benchmark": {"adapter": "jsonl", "path": "items.jsonl"},
                "model": {"id": "m", "adapter": "replay"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path.parent)
    spec = load_spec(tmp_path / "audit.json")
    assert Path(str(spec.benchmark["path"])).exists()


def test_load_spec_reports_concise_errors(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"benchmark": {}, "model": {"adapter": "replay"}}), encoding="utf-8")
    with pytest.raises(ValueError, match=r"invalid audit spec .*model\.id"):
        load_spec(bad)
    bad.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a JSON or YAML object"):
        load_spec(bad)


def test_jsonl_errors_name_the_line(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    items = tmp_path / "broken.jsonl"
    items.write_text(
        '{"id": "a", "prompt": "p", "expected_output": "x"}\n{oops\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match=r"broken\.jsonl:2: invalid JSON"):
        audit(spec.model_copy(update={"benchmark": {"adapter": "jsonl", "path": str(items)}}))
    row = {"id": "a", "prompt": "p", "expected_output": "z", "choices": [{"id": "x", "text": "t"}]}
    items.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"broken\.jsonl:1:"):
        audit(spec.model_copy(update={"benchmark": {"adapter": "jsonl", "path": str(items)}}))


def test_transform_lineage_matches_scored_answer_keys(tmp_path: Path) -> None:
    spec = _spec(tmp_path, transformations=("choice_label_remap", "choice_permutation"))
    report = audit(spec)
    children = {t.child_item_id: t for t in report.transformations}
    items = {
        d.item.id: d.item
        for name in ("choice_label_remap", "choice_permutation")
        for d in generate(audit(spec).benchmark.items, name, 1, 42)
    }
    for child_id, transformation in children.items():
        assert transformation.expected_output == items[child_id].expected_output
