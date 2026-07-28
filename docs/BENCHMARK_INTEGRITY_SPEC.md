# Veritas v2: benchmark integrity

Veritas v2 audits evidence about benchmark integrity; it does not determine intent or claim a model is contaminated from a score drop alone. An audit records canonical, transformed, and optional fresh/temporal performance alongside detector-specific assumptions, alternatives, uncertainty, and provenance.

The v2 root contracts are `BenchmarkItem`, `Benchmark`, `ModelTarget`, `ModelResponse`, `Transformation`, `DetectorFinding`, and schema-versioned `AuditReport`. The pipeline is load → validate → canonical evaluation → transformations → transformed evaluation → detectors → aggregation → report. Optional requirements produce `not_run`, never silent omission.

## Initial workflow

```bash
veritas inspect --config audit.json
veritas audit --config audit.json --out audit-run/
```

Use `--acknowledge-external-transfer` only when a private benchmark is intentionally sent to a configured external endpoint.
