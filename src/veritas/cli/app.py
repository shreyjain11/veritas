"""The ``veritas`` CLI (typer). Thin IO wrappers over the shared audit runners.

audit (full pipeline) / leakage (detection only) / rescore + stratify (operate on a
precomputed contamination graph, no binary). All real work lives in veritas.audit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from veritas.audit.gate import evaluate_gate
from veritas.audit.io_helpers import write_report
from veritas.audit.runners import audit_from_files, audit_on_precomputed_graph, detect_from_files
from veritas.contracts import MetricName, SeqType

app = typer.Typer(help="Veritas: post-hoc leakage & robustness auditor.")

_Seq = Annotated[Path, typer.Option(exists=True, help="eval sequences FASTA")]
_Table = Annotated[Path, typer.Option(exists=True, help="id,label,prediction table")]
_Ref = Annotated[Path, typer.Option(exists=True, help="reference sequences FASTA")]
_Cfg = Annotated[Path, typer.Option(exists=True, help="AuditConfig JSON")]
_Graph = Annotated[Path, typer.Option(exists=True, help="precomputed ContaminationGraph JSON")]
_Out = Annotated[Path, typer.Option(help="output report path")]
_SeqType = Annotated[SeqType, typer.Option(help="sequence alphabet")]
_Metric = Annotated[MetricName, typer.Option(help="headline metric")]
_Fmt = Annotated[str, typer.Option("--format", help="json | md | html")]
_Axis = Annotated[str, typer.Option(help="difficulty axis")]


@app.command()
def audit(
    sequences: _Seq,
    table: _Table,
    reference: _Ref,
    config: _Cfg,
    out: _Out,
    seq_type: _SeqType = SeqType.PROTEIN,
    metric: _Metric = MetricName.AUROC,
    fmt: _Fmt = "json",
) -> None:
    """Run the full pipeline (detection -> de-leak -> honest -> stratify -> report)."""
    report = audit_from_files(
        sequences=sequences,
        table=table,
        reference=reference,
        config=config,
        seq_type=seq_type,
        metric=metric,
    )
    write_report(report, out, fmt)


@app.command()
def leakage(
    sequences: _Seq,
    reference: _Ref,
    config: _Cfg,
    out: _Out,
    seq_type: _SeqType = SeqType.PROTEIN,
) -> None:
    """Run detection only and write the contamination graph."""
    graph = detect_from_files(
        sequences=sequences, reference=reference, config=config, seq_type=seq_type
    )
    out.write_text(graph.model_dump_json(indent=2), encoding="utf-8")


@app.command()
def rescore(
    sequences: _Seq,
    table: _Table,
    graph: _Graph,
    out: _Out,
    seq_type: _SeqType = SeqType.PROTEIN,
    metric: _Metric = MetricName.ACCURACY,
    fmt: _Fmt = "json",
) -> None:
    """Recompute the honest metric against a precomputed contamination graph."""
    report = audit_on_precomputed_graph(
        sequences=sequences, table=table, graph=graph, seq_type=seq_type, metric=metric, axes=()
    )
    write_report(report, out, fmt)


@app.command()
def stratify(
    sequences: _Seq,
    table: _Table,
    graph: _Graph,
    out: _Out,
    seq_type: _SeqType = SeqType.PROTEIN,
    metric: _Metric = MetricName.ACCURACY,
    axis: _Axis = "identity_to_nearest_reference",
    fmt: _Fmt = "json",
) -> None:
    """Stratified robustness analysis against a precomputed contamination graph."""
    report = audit_on_precomputed_graph(
        sequences=sequences,
        table=table,
        graph=graph,
        seq_type=seq_type,
        metric=metric,
        axes=(axis,),
    )
    write_report(report, out, fmt)


@app.command()
def gate(
    report: Annotated[Path, typer.Option(exists=True, help="audit report JSON")],
    max_delta: Annotated[float, typer.Option(help="max allowed reported-honest delta")],
) -> None:
    """Fail (exit 1) if the reported-honest delta exceeds max-delta, or honest is undefined."""
    data = json.loads(report.read_text(encoding="utf-8"))
    passed, message = evaluate_gate(data, max_delta)
    typer.echo(message)
    if not passed:
        raise typer.Exit(code=1)
