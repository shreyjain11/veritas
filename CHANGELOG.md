# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-27

First public packaged release. Veritas v2 adds a model-agnostic benchmark-integrity
system while retaining the established biological audit engine as a supported
legacy domain. The validation suite contains more than 600 collected tests and a
90% coverage gate. No results are fabricated.

### Added

- **Benchmark-integrity v2** — schema-versioned benchmark, model-response,
  transformation, finding, evidence-matrix, score, and provenance contracts.
- **Frontier-model workflow** — benchmark catalog, replay/OpenAI-compatible/local
  model adapters, deterministic transformations, resumable cache, statistical
  comparisons, privacy inspection, and schema-v2 evidence packages.
- **Browser audit console** — BYOK hosted audits for allowlisted providers and
  public benchmarks, with bounded request counts and ephemeral secret handling.
- **Web interaction polish** — accessible scroll-reveal and hover/focus
  micro-interactions that respect `prefers-reduced-motion`.
- **Schema-v2 report viewer** — executive scores, findings, evidence matrix,
  transformation validity, item evidence, limitations, and provenance, alongside
  the distinct legacy-v1 viewer.

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
