# API

Veritas is usable as a library. The core entry point runs the full pipeline and
returns a typed, frozen report.

## Run an audit programmatically

```python
from pathlib import Path

from veritas.audit import run_audit
from veritas.contracts import AuditConfig, DetectorConfig, DetectorKind

config = AuditConfig(
    detectors=(
        DetectorConfig(kind=DetectorKind.SEQUENCE, name="mmseqs", identity_threshold=0.3),
    ),
    seed=1729,
)

report = run_audit(
    sequences=Path("eval.fasta"),
    table=Path("table.csv"),
    reference=Path("reference.fasta"),
    config=config,
    metric="auroc",
)

print(report.reported.value, report.honest.value)
print(report.audit_hash)
```

## Key contracts

All contracts are frozen pydantic models (`frozen=True, extra="forbid"`), so
reports are immutable and structurally validated.

- **`AuditConfig`** — detectors, `seed`, `combine_policy`, `deleak_policy`,
  bootstrap settings, `stratify_axes`, and `pinned_versions`.
- **`DetectorConfig`** — one detector's kind, name, and thresholds.
- **`ContaminationGraph` / `ContaminationEdge`** — detected leakage.
- **`AuditReport`** — `reported`, `honest`, `leakage`, stratification,
  `limitations`, `provenance`, and `audit_hash`.
- **`Limitation`** — a disclosed methodological caveat (hashed into the report).

## Optional surfaces

- **CLI** (`cli` extra) — the `veritas` command; see [Usage](usage.md).
- **MCP** (`mcp` extra) — exposes the auditor as an MCP server.

Both are import-isolated: the core library does not import them, so a core-only
install stays dependency-light.
