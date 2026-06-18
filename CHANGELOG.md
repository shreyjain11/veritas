# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-18

First packaged release. The audit engine and its interfaces are complete and
validated by the test suite (100% coverage; `ruff`, `ruff format`, and
`mypy --strict` all gate). The demonstration suite and external reproductions
are in progress pending benchmark finalization — no demonstration or
reproduction results are reported yet (see `docs/validation.md`).

### Added

- **Audit pipeline** — `veritas.audit.run_audit`: detect leakage → de-leak →
  honest re-score → stratify → signed report.
- **Detectors** — sequence-identity (MMseqs2), family (HMMER), and structural
  (Foldseek) contamination detectors behind a common interface, combined into a
  single contamination graph; MinHash/LSH candidate prefilter for the sequence
  backends.
- **Honest re-scoring** with percentile-bootstrap confidence intervals, and
  distance-to-nearest-reference stratification.
- **Provenance & determinism** — every reported number carries a
  `provenance_ref`; the whole report is covered by an `audit_hash`; reports are
  byte-identical on the pinned platform. Each detector records the resolved
  absolute path of its binary in provenance.
- **Disclosed limitations** — measured bootstrap-coverage and prefilter-recall
  caveats travel inside the report (and are hashed into it).
- **CLI** (`cli` extra) — `veritas audit | leakage | rescore | stratify | gate`.
  `veritas gate` fails a CI build when the reported-vs-honest gap exceeds a
  threshold, and fails loudly when the honest metric is undefined or there is
  insufficient clean data.
- **MCP server** (`mcp` extra) — the auditor exposed as MCP tools.
- **GitHub Action** — a composite action (`action.yml`) wrapping audit + gate
  for drop-in CI use, with a runnable `examples/quickstart/` dataset.
- **Documentation** (`docs` extra) — mkdocs-material site, including a
  limitations & guarantees page.

[0.1.0]: https://github.com/shreyjain11/veritas/releases/tag/v0.1.0
