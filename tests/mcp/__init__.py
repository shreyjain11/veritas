"""Phase 7 MCP-server tests + shared hermetic fixtures (no SDK import here)."""

from __future__ import annotations

from pathlib import Path

from veritas.contracts import (
    AuditConfig,
    ContaminationEdge,
    ContaminationGraph,
    DetectorConfig,
    DetectorKind,
)


def planted_graph(detector_id: str) -> ContaminationGraph:
    """A one-edge graph contaminating eval id 'a' (matches write_audit_fixtures)."""
    return ContaminationGraph(
        edges=(
            ContaminationEdge(
                eval_id="a",
                ref_id="r",
                score=1.0,
                kind=DetectorKind.SEQUENCE,
                detector_id=detector_id,
            ),
        )
    )


def write_audit_fixtures(tmp_path: Path, detector_name: str) -> None:
    """eval FASTA + label/prediction table + reference FASTA + an AuditConfig JSON."""
    (tmp_path / "eval.fasta").write_text(">a\nMKVLA\n>b\nMKVLC\n", encoding="utf-8")
    (tmp_path / "table.csv").write_text("id,label,prediction\na,1,0.9\nb,1,0.1\n", encoding="utf-8")
    (tmp_path / "reference.fasta").write_text(">r\nMKVLA\n", encoding="utf-8")
    config = AuditConfig(
        detectors=(
            DetectorConfig(kind=DetectorKind.SEQUENCE, name=detector_name, identity_threshold=0.5),
        ),
        seed=1729,
    )
    (tmp_path / "config.json").write_text(config.model_dump_json(), encoding="utf-8")


def write_graph(tmp_path: Path, detector_id: str = "x") -> None:
    (tmp_path / "graph.json").write_text(
        planted_graph(detector_id).model_dump_json(), encoding="utf-8"
    )
