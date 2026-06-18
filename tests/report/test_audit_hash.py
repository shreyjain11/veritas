"""(1) The audit_hash covers the limitations: changing them changes the hash.

collect_limitations runs during assembly *before* the hash is computed, so the
hash is a function of the disclosed caveats too -- stripping or swapping a
limitation must flip audit_hash, and an assembled report's stored hash must equal
a fresh recomputation.
"""

from __future__ import annotations

from tests.factories import make_audit_report, make_golden_audit
from veritas.audit import run_audit
from veritas.report import audit_hash_for


def test_assembled_hash_matches_recomputation() -> None:
    report = make_audit_report()
    assert report.audit_hash == audit_hash_for(report)


def test_audit_hash_is_deterministic() -> None:
    assert make_audit_report().audit_hash == make_audit_report().audit_hash


def test_stripping_a_limitation_changes_the_hash() -> None:
    full = make_audit_report(prefilter_enabled=True)
    assert len(full.limitations) >= 2
    stripped = full.model_copy(update={"limitations": full.limitations[:-1]})
    # Everything else is held fixed, so only the dropped limitation can move the hash.
    assert audit_hash_for(stripped) != audit_hash_for(full)


def test_two_reports_differing_only_in_limitations_have_different_hash() -> None:
    base = make_audit_report(prefilter_enabled=True)
    none = base.model_copy(update={"limitations": ()})
    assert audit_hash_for(none) != audit_hash_for(base)


def test_a_stratum_metric_change_changes_the_audit_hash() -> None:
    # Decision 1: stratification is hashed -- changing one stratum's metric moves the hash.
    case = make_golden_audit()
    report = run_audit(
        case.config,
        case.inputs,
        detector_factory=case.detector_factory,
        version_runner=case.version_runner,
    )
    strata = list(report.stratification)
    index = next(i for i, s in enumerate(strata) if s.metric.value is not None)
    stratum = strata[index]
    current = stratum.metric.value
    assert current is not None
    bumped_metric = stratum.metric.model_copy(update={"value": current + 0.125})
    strata[index] = stratum.model_copy(update={"metric": bumped_metric})
    bumped = report.model_copy(update={"stratification": tuple(strata)})
    assert audit_hash_for(bumped) != audit_hash_for(report)
