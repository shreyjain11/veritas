"""End-to-end + differential tests for the structural detector against real foldseek.

Marked ``requires_foldseek`` (auto-skipped offline). Vendored structures:
``ref1.pdb`` (reference fold) and ``decoy.pdb`` (an unrelated fold). The
near-duplicate ``eval_close`` is generated here from ``ref1.pdb`` by a pinned,
seeded coordinate perturbation, and the test asserts the measured TM-score lands
in a defined band (above threshold, below 1.0) before asserting the edge — so the
fixture cannot silently become trivial (TM~1.0) or fold-destroying (TM<threshold).

Calibration guard (``test_foldseek_self_match_tm_is_calibrated``): the detector reads
foldseek's ``qtmscore``/``ttmscore`` (a true TM-score, <= 1.0) under ``--alignment-type 1``,
NOT the uncalibrated ``alntmscore`` (which exceeds 1.0 for strong/identical matches). A
self-match must score ~1.0 and never above it. The original band test missed this because
its single perturbed pair scored ~0.88 under either field, and it used only single-chain
structures so the per-chain id-stripping bug never fired either.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from veritas.contamination.backends.foldseek import FoldseekSearch
from veritas.contamination.graph import contaminated_eval_ids
from veritas.contamination.structural import StructuralDetector
from veritas.contracts import DetectorConfig, DetectorKind, EvalItem, ReferenceItem, SeqType

pytestmark = pytest.mark.requires_foldseek

_STRUCTURES = Path(__file__).parent.parent / "fixtures" / "contamination" / "structures"

# Perturbation calibrated against foldseek 10.941cd33 on ref1.pdb (crambin/1CRN):
# sigma=0.7 A with this seed yields TM=0.8867 (in band); sigma>=0.9 destroys the
# fold (no alignment). The band assertion below keeps this honest if it ever drifts.
_PERTURB_SIGMA_ANGSTROM = 0.7
_PERTURB_SEED = 20260615
_TM_BAND = (0.7, 0.9)
_SCORE_THRESHOLD = 0.5  # strictly below the band, so a near-duplicate forms an edge


def _perturb_pdb(text: str, *, sigma: float, seed: int) -> str:
    rng = np.random.default_rng(seed)
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith(("ATOM", "HETATM")) and len(line) >= 54:
            x = float(line[30:38]) + float(rng.normal(0.0, sigma))
            y = float(line[38:46]) + float(rng.normal(0.0, sigma))
            z = float(line[46:54]) + float(rng.normal(0.0, sigma))
            line = f"{line[:30]}{x:8.3f}{y:8.3f}{z:8.3f}{line[54:]}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def _config() -> DetectorConfig:
    return DetectorConfig(
        kind=DetectorKind.STRUCTURE, name="foldseek", score_threshold=_SCORE_THRESHOLD
    )


def test_foldseek_golden_recovers_perturbed_fold_within_tm_band(tmp_path: Path) -> None:
    ref1 = _STRUCTURES / "ref1.pdb"
    eval_close = tmp_path / "eval_close.pdb"
    eval_close.write_text(
        _perturb_pdb(ref1.read_text(), sigma=_PERTURB_SIGMA_ANGSTROM, seed=_PERTURB_SEED)
    )

    evals = (
        EvalItem(
            id="e_close",
            sequence="MKVLA",
            seq_type=SeqType.PROTEIN,
            label=1.0,
            structure_path=eval_close,
        ),
        EvalItem(
            id="e_decoy",
            sequence="MKVLA",
            seq_type=SeqType.PROTEIN,
            label=0.0,
            structure_path=_STRUCTURES / "decoy.pdb",
        ),
    )
    refs = (
        ReferenceItem(id="r1", sequence="MKVLA", seq_type=SeqType.PROTEIN, structure_path=ref1),
    )

    graph = StructuralDetector(search=FoldseekSearch()).detect(evals, refs, _config())

    close_edges = [e for e in graph.edges if e.eval_id == "e_close" and e.ref_id == "r1"]
    assert close_edges, "perturbed copy should still align to its source structure"
    measured_tm = close_edges[0].score
    assert _TM_BAND[0] <= measured_tm <= _TM_BAND[1], (
        f"measured TM {measured_tm} outside calibrated band {_TM_BAND}: "
        "the fixture became trivial or fold-destroying"
    )

    contaminated = contaminated_eval_ids(graph)
    assert "e_close" in contaminated
    assert "e_decoy" not in contaminated


def test_foldseek_self_match_tm_is_calibrated(tmp_path: Path) -> None:
    # A structure vs an identical copy: a true TM-score is exactly 1.0. The uncalibrated
    # alntmscore exceeds 1.0 here (observed up to ~1.05), so this fails unless the backend
    # reads the calibrated qtmscore/ttmscore. Guards against a mislabeled/uncalibrated score.
    ref1 = _STRUCTURES / "ref1.pdb"
    copy = tmp_path / "copy.pdb"
    copy.write_text(ref1.read_text())
    evals = (
        EvalItem(
            id="e_self", sequence="MKVLA", seq_type=SeqType.PROTEIN, label=1.0, structure_path=copy
        ),
    )
    refs = (
        ReferenceItem(id="r1", sequence="MKVLA", seq_type=SeqType.PROTEIN, structure_path=ref1),
    )
    graph = StructuralDetector(search=FoldseekSearch()).detect(evals, refs, _config())
    edges = [e for e in graph.edges if e.eval_id == "e_self" and e.ref_id == "r1"]
    assert edges, "identical structures must align"
    tm = edges[0].score
    assert 0.99 <= tm <= 1.0, (
        f"self-match TM {tm} is not a calibrated TM-score (must be ~1.0, <=1.0)"
    )


def test_foldseek_specificity_unrelated_fold_yields_no_edges() -> None:
    evals = (
        EvalItem(
            id="e_decoy",
            sequence="MKVLA",
            seq_type=SeqType.PROTEIN,
            label=0.0,
            structure_path=_STRUCTURES / "decoy.pdb",
        ),
    )
    refs = (
        ReferenceItem(
            id="r1",
            sequence="MKVLA",
            seq_type=SeqType.PROTEIN,
            structure_path=_STRUCTURES / "ref1.pdb",
        ),
    )
    graph = StructuralDetector(search=FoldseekSearch()).detect(evals, refs, _config())
    assert graph.edges == ()


def test_foldseek_reports_runtime_version() -> None:
    assert FoldseekSearch().version()
