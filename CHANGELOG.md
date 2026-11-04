# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **v2 findings** — the perturbation finding was reported twice, and an audit with no
  transformations crashed; each detector now runs exactly once.
- **Verdicts need evidence** — "supports" requires a 95% interval above zero and a
  Benjamini-Hochberg-corrected p ≤ 0.05; an interval below the 5-point equivalence margin
  is evidence against; fewer than 10 paired items stays inconclusive. Previously any
  positive gap, however small the sample, was reported as supporting evidence.
- **Paired scoring** — the robustness gap is computed on truly paired items, and missing or
  errored responses are excluded instead of being scored as wrong answers.
- **Transformations** — choice permutation always moves the correct answer (it was often a
  no-op); label remapping records the child's answer key in lineage; identifier renaming is
  bijective (distinct variables were collapsed into one name).
- **Answer parsing** — "The answer is B", "Answer: (B)", `**C**`, and restated option text
  are understood; unparseable output is no longer coerced into a label. Parsing is
  linear-time, so adversarial model output cannot stall an audit.
- **OpenAI-compatible adapter** — no longer sends an invalid `extra` field, honors the system
  prompt, tolerates null content, retries transient errors, and fails fast on auth errors.
- **Evidence matrix** — reports the strongest (not weakest) supporting strength and fills the
  contradicting column.
- **Replay reports** — no longer copy the whole replay table into every response.
- `veritas gate` no longer crashes on schema-v2 reports.
- **`mcp` extra** — capped at `mcp<2`: the 2.x SDK removed APIs the server relies on, so
  `pip install veritas-leakage[mcp]` (and CI's installed-wheel job) pulled an incompatible
  release.
- **Determinism** — v2 scores use exactly rounded summation, so reports and their hashes
  are byte-identical on Python 3.11, 3.12, and 3.13.

### Added

- `audit_hash` covers the entire v2 report and is verifiable in Python (`veritas verify`,
  MCP `verify_report`) and in the browser viewer.
- Hosted runner: Anthropic, Google Gemini, xAI, Mistral, and DeepSeek providers; up to 50
  items; output budgets and parameter handling for reasoning models; time-budgeted partial
  results; the full interactive report in place after a run.
- Viewer: integrity badge, drag-and-drop, a bundled sample report, item filters (flipped by a
  variant / wrong / errors), per-variant correctness, and per-family breakdowns.

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
