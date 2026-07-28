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
from veritas.benchmark_integrity.catalog import CATALOG, list_benchmarks
from veritas.benchmark_integrity.reporting import (
    render_html,
    render_markdown,
)
from veritas.benchmark_integrity.reporting import (
    render_json as render_v2_json,
)
from veritas.benchmark_integrity.service import audit as audit_v2
from veritas.benchmark_integrity.service import (
    inspect_audit,
    load_benchmark,
    load_spec,
)
from veritas.benchmark_integrity.transforms import generate
from veritas.contracts import MetricName, SeqType

app = typer.Typer(
    help="Veritas: benchmark-integrity auditor. Legacy biological commands remain available."
)
legacy_app = typer.Typer(help="Legacy domain workflows.")
bio_app = typer.Typer(help="Sequence-based biological leakage auditor.")
legacy_app.add_typer(bio_app, name="bio")
app.add_typer(legacy_app, name="legacy")

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
    config: _Cfg,
    out: _Out,
    acknowledge_external_transfer: Annotated[
        bool, typer.Option(help="acknowledge private data transfer to an external endpoint")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option(help="estimate requests, cost bounds, and privacy warnings only")
    ] = False,
    sequences: _Seq | None = None,
    table: _Table | None = None,
    reference: _Ref | None = None,
    seq_type: _SeqType = SeqType.PROTEIN,
    metric: _Metric = MetricName.AUROC,
    fmt: _Fmt = "json",
) -> None:
    """Run a v2 benchmark-integrity audit; legacy sequence flags remain supported."""
    if sequences is not None or table is not None or reference is not None:
        if sequences is None or table is None or reference is None:
            raise typer.BadParameter(
                "legacy audit requires --sequences, --table, and --reference together"
            )
        legacy_report = audit_from_files(
            sequences=sequences,
            table=table,
            reference=reference,
            config=config,
            seq_type=seq_type,
            metric=metric,
        )
        write_report(legacy_report, out, fmt)
        return
    spec = load_spec(config)
    if dry_run:
        typer.echo(json.dumps(inspect_audit(spec), indent=2, sort_keys=True))
        return
    v2_report = audit_v2(spec, acknowledge_external_transfer=acknowledge_external_transfer)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(render_v2_json(v2_report), encoding="utf-8")
    (out / "report.md").write_text(render_markdown(v2_report), encoding="utf-8")
    (out / "report.html").write_text(render_html(v2_report), encoding="utf-8")
    typer.echo(f"wrote {out / 'report.json'}")


@app.command("inspect")
def inspect(config: _Cfg) -> None:
    """Validate and estimate a v2 audit before it makes model requests."""
    typer.echo(json.dumps(inspect_audit(load_spec(config)), indent=2, sort_keys=True))


@app.command("adapters")
def adapters() -> None:
    """List built-in v2 model adapters."""
    typer.echo("replay\nopenai_compatible\nvllm\nhuggingface_local")


@app.command("detectors")
def detectors() -> None:
    """List currently available v2 detector families."""
    typer.echo(
        "exact_match\nperturbation\nprobability\nguided_completion\noption_order\n"
        "template_dependence\nfresh_set\ntemporal\nerror_reproduction\ncross_model\n"
        "evaluator_exploitation\nconsistency"
    )


@app.command("benchmarks")
def benchmarks(
    name: Annotated[str | None, typer.Argument(help="optional catalog benchmark name")] = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="emit machine-readable catalog metadata")
    ] = False,
) -> None:
    """List built-in benchmark presets without downloading their data."""
    if name is not None:
        entry = CATALOG.get(name)
        if entry is None:
            raise typer.BadParameter(f"unknown benchmark {name!r}; available: {', '.join(CATALOG)}")
        typer.echo(json.dumps(entry.public_dict(), indent=2, sort_keys=True))
        return
    rows = list_benchmarks()
    if as_json:
        typer.echo(json.dumps(rows, indent=2, sort_keys=True))
        return
    for row in rows:
        access = "auth" if row["requires_auth"] else "public"
        typer.echo(f"{row['name']:<20} {row['task_type']:<16} {access:<6} {row['description']}")


@app.command("evaluate")
def evaluate(
    config: _Cfg,
    out: _Out,
    acknowledge_external_transfer: bool = False,
) -> None:
    """Evaluate the canonical benchmark portion of a v2 audit specification."""
    spec = load_spec(config)
    report = audit_v2(spec, acknowledge_external_transfer=acknowledge_external_transfer)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(render_v2_json(report), encoding="utf-8")
    (out / "report.md").write_text(render_markdown(report), encoding="utf-8")
    (out / "report.html").write_text(render_html(report), encoding="utf-8")


@app.command("transform")
def transform(config: _Cfg, out: _Out) -> None:
    """Generate reproducible transformed items and their lineage records."""
    spec = load_spec(config)
    benchmark = load_benchmark(spec.benchmark)
    seed = int(spec.runtime.get("seed", 42))
    derived = [
        value
        for transform_spec in spec.transformations
        for value in generate(
            benchmark.items,
            transform_spec.type,
            transform_spec.variants_per_item,
            seed,
        )
    ]
    out.write_text(
        json.dumps(
            [
                {
                    "item": value.item.model_dump(mode="json"),
                    "transformation": value.transformation.model_dump(mode="json"),
                }
                for value in derived
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


@app.command("validate-transformations")
def validate_transformations(config: _Cfg, out: _Out) -> None:
    """Emit deterministic transformation-validation statuses for a v2 spec."""
    transform(config, out)


@app.command("detect")
def detect(config: _Cfg, out: _Out, acknowledge_external_transfer: bool = False) -> None:
    """Run configured v2 detectors and write their explicit findings."""
    report = audit_v2(
        load_spec(config), acknowledge_external_transfer=acknowledge_external_transfer
    )
    out.write_text(
        json.dumps(
            [item.model_dump(mode="json") for item in report.findings], indent=2, sort_keys=True
        )
        + "\n",
        encoding="utf-8",
    )


@app.command("compare")
def compare(
    reports: Annotated[list[Path], typer.Option("--report", exists=True)],
    out: _Out,
) -> None:
    """Compare canonical and robust scores across schema-v2 report JSON files."""
    rows = []
    for path in reports:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != "2.0":
            raise typer.BadParameter(f"{path} is not a schema-v2 report")
        rows.append(
            {"report": str(path), "benchmark": data["benchmark"]["id"], "score": data["score"]}
        )
    out.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@app.command("report")
def report(report_json: Annotated[Path, typer.Option(exists=True)], out: _Out) -> None:
    """Copy a validated report artifact to a chosen output path."""
    data = json.loads(report_json.read_text(encoding="utf-8"))
    if data.get("schema_version") != "2.0":
        raise typer.BadParameter("report command currently renders schema-v2 report JSON")
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@bio_app.command("audit")
def legacy_bio_audit(
    sequences: _Seq,
    table: _Table,
    reference: _Ref,
    config: _Cfg,
    out: _Out,
    seq_type: _SeqType = SeqType.PROTEIN,
    metric: _Metric = MetricName.AUROC,
    fmt: _Fmt = "json",
) -> None:
    """Run the preserved biological audit workflow."""
    write_report(
        audit_from_files(
            sequences=sequences,
            table=table,
            reference=reference,
            config=config,
            seq_type=seq_type,
            metric=metric,
        ),
        out,
        fmt,
    )


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
