"""Detector registry: built-ins are registered and share the common interface."""

from __future__ import annotations

import pytest

from veritas.contamination.base import ContaminationDetector
from veritas.contamination.registry import (
    available_detectors,
    get_detector,
    register_detector,
)
from veritas.contracts import DetectorKind, SeqType

_EXPECTED_KIND = {
    "mmseqs": DetectorKind.SEQUENCE,
    "diamond": DetectorKind.SEQUENCE,
    "pyhmmer": DetectorKind.FAMILY,
    "foldseek": DetectorKind.STRUCTURE,
}


def test_builtin_detectors_are_registered() -> None:
    assert set(_EXPECTED_KIND).issubset(set(available_detectors()))


@pytest.mark.parametrize("name", sorted(_EXPECTED_KIND))
def test_each_detector_implements_interface(name: str) -> None:
    detector = get_detector(name)
    assert isinstance(detector, ContaminationDetector)
    assert detector.kind is _EXPECTED_KIND[name]
    assert detector.supported_alphabets <= {SeqType.PROTEIN, SeqType.NUCLEOTIDE}


def test_sequence_detectors_support_both_alphabets() -> None:
    assert get_detector("mmseqs").supported_alphabets == {SeqType.PROTEIN, SeqType.NUCLEOTIDE}


def test_family_and_structure_detectors_are_protein_only() -> None:
    assert get_detector("pyhmmer").supported_alphabets == {SeqType.PROTEIN}
    assert get_detector("foldseek").supported_alphabets == {SeqType.PROTEIN}


def test_unknown_detector_raises() -> None:
    with pytest.raises(KeyError):
        get_detector("does-not-exist")


def test_register_detector_makes_it_available() -> None:
    detector = get_detector("mmseqs")
    register_detector("custom-registered", lambda: detector)
    assert "custom-registered" in available_detectors()
    assert get_detector("custom-registered") is detector
