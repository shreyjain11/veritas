"""AuditConfig / DetectorConfig: required seed, per-kind threshold validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veritas.contracts import (
    AuditConfig,
    CombinePolicy,
    DeLeakPolicy,
    DetectorConfig,
    DetectorKind,
)


def _seq_detector() -> DetectorConfig:
    return DetectorConfig(
        kind=DetectorKind.SEQUENCE,
        name="mmseqs",
        identity_threshold=0.3,
        coverage_threshold=0.5,
    )


def test_minimal_valid_config() -> None:
    cfg = AuditConfig(detectors=(_seq_detector(),), seed=1729)
    assert cfg.seed == 1729
    assert len(cfg.detectors) == 1


def test_requires_seed() -> None:
    with pytest.raises(ValidationError):
        AuditConfig(detectors=(_seq_detector(),))  # type: ignore[call-arg]


def test_rejects_empty_detectors() -> None:
    with pytest.raises(ValidationError):
        AuditConfig(detectors=(), seed=1)


def test_default_policies() -> None:
    cfg = AuditConfig(detectors=(_seq_detector(),), seed=1)
    assert cfg.combine_policy is CombinePolicy.UNION
    assert cfg.deleak_policy is DeLeakPolicy.DROP


def test_bootstrap_n_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        AuditConfig(detectors=(_seq_detector(),), seed=1, bootstrap_n=0)


def test_ci_level_must_be_in_unit_interval() -> None:
    with pytest.raises(ValidationError):
        AuditConfig(detectors=(_seq_detector(),), seed=1, ci_level=1.5)


def test_sequence_detector_requires_identity_threshold() -> None:
    with pytest.raises(ValidationError):
        DetectorConfig(kind=DetectorKind.SEQUENCE, name="mmseqs")


def test_family_detector_requires_evalue() -> None:
    with pytest.raises(ValidationError):
        DetectorConfig(kind=DetectorKind.FAMILY, name="pyhmmer")


def test_structure_detector_requires_score() -> None:
    with pytest.raises(ValidationError):
        DetectorConfig(kind=DetectorKind.STRUCTURE, name="foldseek")


def test_identity_threshold_range() -> None:
    with pytest.raises(ValidationError):
        DetectorConfig(
            kind=DetectorKind.SEQUENCE,
            name="mmseqs",
            identity_threshold=1.5,
            coverage_threshold=0.5,
        )


def test_evalue_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        DetectorConfig(kind=DetectorKind.FAMILY, name="pyhmmer", e_value_threshold=0.0)


def test_round_trip_json() -> None:
    cfg = AuditConfig(detectors=(_seq_detector(),), seed=1)
    assert AuditConfig.model_validate_json(cfg.model_dump_json()) == cfg
