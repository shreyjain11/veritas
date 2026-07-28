# Migration guide: v1 biological auditor to v2

`veritas audit` now accepts a schema-v2 audit configuration and writes an audit directory containing `report.json`. Existing sequence audits continue to work when invoked with `--sequences`, `--table`, and `--reference`; they should migrate to `veritas legacy bio` when that compatibility command becomes available.

V1 reports remain valid legacy artifacts. V2 reports carry `schema_version: "2.0"` and must be handled as benchmark-integrity evidence, not biological leakage reports.
