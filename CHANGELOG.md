# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Web report viewer polish** — fill-in bars on the reported/honest collapse
  and leakage meters, scroll-reveal for the landing page's proof cards and
  how-it-works steps, and small hover/focus micro-interactions across the
  nav and report cards. All motion respects `prefers-reduced-motion`.

## [0.1.0] - 2026-06-18

First packaged release. The audit engine, its interfaces, and the validation
suite are complete (comprehensive coverage behind a ≥90% gate; `ruff`,
`ruff format`, and `mypy --strict` all gate). Four demonstrations report real,
locked numbers on pinned data — OverfitNN homology inflation, genomic
reverse-complement detection, ProteinGym MSA-depth stratification, and PPI
family + structural leakage (see `docs/validation.md`). No results are fabricated.

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
- **Documentation & web report viewer** — an in-browser viewer + project site
  ([veritas-viewer.vercel.app](https://veritas-viewer.vercel.app), docs at
  `/docs`) that re-verifies each report's `audit_hash` client-side; plus an
  in-repo mkdocs reference (`docs` extra).
- **Packaging & distribution** — distributed as `veritas-leakage`
  (`pip install "veritas-leakage[cli]"`; the import package and the `veritas`
  command are unchanged), and a batteries-included Docker image at
  `ghcr.io/shreyjain11/veritas-leakage` that bakes in the pinned detector
  binaries so it runs on any OS with no conda setup.

[0.1.0]: https://github.com/shreyjain11/veritas/releases/tag/v0.1.0
