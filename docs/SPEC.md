# Veritas — Architecture & Build Specification

A model-agnostic, post-hoc **leakage & robustness auditor** for sequence-based
biological predictors. This document is the source of truth for what gets built
and in what order. Read alongside `CLAUDE.md`.

---

## 1. The problem, precisely

Published ML-bio models report headline metrics on benchmarks whose evaluation
sets often contain items that are evolutionarily/structurally close to what the
model already "knows" (its training or reference set). Random or naive splitting
leaks this signal, inflating reported performance. Tools exist to *build*
leakage-free splits proactively (GraphPart, DataSAIL, SpanSeq, hashFrag), but
there is no clean, reusable, agent-runnable tool to *audit an existing model +
benchmark after the fact* and answer:

- How much of this evaluation set is contaminated by homology to the reference
  set, and which items?
- What is the model's **honest** metric once that contamination is removed, and
  how big is the gap to the reported number?
- In which **difficulty regime** does the model silently fail, even where the
  aggregate metric looks fine?

Veritas is that instrument. The novelty (and the basis for a preprint) is the
post-hoc audit framing plus the stratified silent-failure analysis as a
reusable, validated instrument — not the surrounding plumbing.

## 2. Core design tenets

- **Model-agnostic core.** The engine knows nothing about any specific model. It
  operates on abstract contracts: a set of *evaluation items* (sequence + label +
  prediction), a *reference set* (sequences/structures the model effectively
  "saw"), one or more *contamination detectors*, and a *metric*. No model,
  benchmark, or organism is privileged; breadth is proven by a demonstration
  suite, not a single case.
- **Provenance-by-construction.** Every computed value carries a record of the
  exact inputs (content-hashed), tool versions, parameters, and random seed used
  to produce it. Reports serialize this manifest.
- **Determinism.** Fixed seed ⇒ identical output and identical provenance hash.
- **Validation you can prove.** Correctness rests on synthetic cases with planted
  ground truth, differential checks against reference tools, and reproduction of
  a published result — not on hand-waving.

## 3. Module architecture

```
veritas/
  contracts/        # pydantic schemas: EvalItem, ReferenceItem, Predictions,
                    # Benchmark, AuditConfig, ProvenanceRecord, AuditReport
  io/               # loaders/adapters: FASTA, prediction tables, split files;
                    # pluggable BenchmarkAdapter / ModelAdapter / ReferenceAdapter
  contamination/    # pluggable contamination detectors over a common interface:
                    #   ContaminationDetector -> ContaminationGraph
                    #     (edges: eval_item <-> ref_item, score, kind, params)
                    #   backends:
                    #     - SequenceIdentityDetector  (mmseqs2 primary, diamond opt.)
                    #     - FamilyDetector            (HMMER/Pfam via pyhmmer)
                    #     - StructuralDetector        (foldseek)
                    #   MinHash (datasketch) candidate pre-filter for scale;
                    #   content-hash caching of expensive searches;
                    #   detectors are composable — an audit may run several and
                    #   union/intersect their contamination graphs.
  metrics/          # metric registry (AUROC, AUPRC, Spearman, etc.),
                    # bootstrap CIs, de-leak policies (drop / stratify / reweight),
                    # reported-vs-honest delta with CI
  stratify/         # difficulty axes (identity-to-nearest-ref, MSA/align depth,
                    # label class) -> performance-vs-difficulty curves
  provenance/       # ProvenanceRecord assembly, content hashing, tool-version
                    # capture, manifest serialization, stable audit hash
  report/           # HTML (self-contained) + JSON + Markdown renderers;
                    # matplotlib SVG figure builders
  audit/            # the orchestrator: config -> full pipeline -> AuditReport
  cli/              # typer app: `veritas audit | leakage | rescore | stratify`
  mcp/              # MCP server exposing: detect_leakage, rescore, stratify,
                    # run_audit, get_provenance
```

Hard rule: `contracts`, `contamination`, `metrics`, `stratify`, `provenance`,
`report`, `audit` must import cleanly with neither `cli` nor `mcp` present.

## 4. Key contracts (shape, not final)

- `EvalItem`: id, sequence, label, prediction, optional metadata.
- `ReferenceItem`: id, sequence, optional provenance of why it's "seen".
- `Benchmark`: eval items + declared split semantics + metric spec.
- `AuditConfig`: which contamination detector(s) to run + their thresholds
  (identity/coverage, family E-value, structural TM/score), de-leak policy,
  bootstrap n, seed, stratification axes, tool choices/versions.
- `ProvenanceRecord`: input hashes, tool versions, params, seed, timestamps.
- `AuditReport`: leakage summary, reported-vs-honest table (with CIs),
  stratification curves, full provenance manifest, stable `audit_hash`.

## 5. Validation strategy (the heart of the project)

Each is a first-class deliverable, not an afterthought:

1. **Unit tests** — every public function; ≥90% coverage gate in CI.
2. **Golden injected-leakage suite** — synthetic benchmarks where leaked pairs and
   the true honest-metric delta are planted by construction. Assert exact
   recovery of leaked edges and the metric delta. The cornerstone.
3. **Property-based tests (Hypothesis)** — invariants: duplicate-in-eval ⇒
   leakage detection cannot decrease; threshold monotonicity; de-leak only
   removes; honest metric ≤ reported under the inflation construction; bootstrap
   CI contains the planted value at the nominal rate.
4. **Differential tests** — each detector's calls cross-checked against a pinned
   reference run of its backend tool (mmseqs2/diamond for sequence, HMMER/Pfam for
   family, foldseek for structural) on fixed datasets; agreement within tolerance.
5. **External reproduction tests** — reproduce ≥2 *published* leakage findings
   end-to-end, spanning different domains and contamination kinds (candidates to
   confirm during planning: a protein-benchmark homology-leakage result; a
   genomic/regulatory cross-chromosome leakage result), each within stated
   tolerance. External validity across model classes, not just internal.
6. **Determinism test** — two identical runs ⇒ identical report + provenance hash.
7. **Scale test** — ≥50k eval items within a documented time/memory budget on the
   target VM.
8. **Report snapshot tests** — rendered report structure is stable; numbers in
   HTML/JSON/MD agree exactly with the computed values.

CI (GitHub Actions) runs the full suite + coverage gate + ruff + `mypy --strict`
on every PR, with mmseqs2/diamond pinned to specific versions.

## 6. Gated phase plan

Build is one complete product, executed in this order. **A phase is finished only
when its full test suite is green, coverage holds, and review/security passes.**

- **Phase 0 — Scaffold.** Repo, `pyproject.toml` (hatchling), `uv` env, `ruff` +
  `mypy --strict`, `pytest` harness, CI skeleton, `CLAUDE.md`, this spec, a
  failing smoke test. Pin mmseqs2/diamond versions.
- **Phase 1 — Contracts + IO + Provenance.** pydantic schemas; FASTA/prediction/
  split loaders; provenance assembly + content hashing + stable audit hash.
  Tests + determinism test for hashing.
- **Phase 2 — Contamination engine.** Common `ContaminationDetector` interface +
  `ContaminationGraph`; MinHash pre-filter; `SequenceIdentityDetector` (mmseqs2)
  first, then `FamilyDetector` (pyhmmer/Pfam) and `StructuralDetector` (foldseek);
  caching; composition (union/intersect). Golden injected-contamination tests per
  detector + differential tests vs each backend. Security-review the subprocess
  boundary.
- **Phase 3 — Metrics + de-leak.** Metric registry, bootstrap CIs, de-leak
  policies, reported-vs-honest delta. Property tests for invariants + CI coverage.
- **Phase 4 — Stratification.** Difficulty axes (similarity-to-nearest-ref per
  detector, alignment/structure depth, label class) + performance-vs-difficulty
  curves. Golden tests where the failure regime is planted.
- **Phase 5 — Report.** HTML/JSON/MD renderers + matplotlib SVG figures + snapshot
  tests + cross-format number-agreement tests.
- **Phase 6 — CLI + demonstration suite.** `veritas` CLI; end-to-end audits across
  ≥3 distinct model/benchmark types exercising all detectors; the external
  reproduction tests.
- **Phase 7 — MCP server.** Expose audit tools over MCP; integration tests that an
  agent-style call path produces a report identical to the CLI path.
- **Phase 8 — Polish.** GitHub Action for CI-droppable audits, mkdocs site,
  packaging, full-suite green on clean checkout, performance pass, final review.

## 7. Open scientific decisions (resolve during planning; do not block engineering)

- For each demonstration model, what is the right "reference set" to measure
  contamination against (declared training data, calibration data, a frequency
  prior, etc.). This is per-adapter, not a core concern.
- Default thresholds and sensible presets for each detector (sequence identity %,
  family E-value, structural score), and how their contamination graphs combine.
- Which 3+ models/benchmarks make the demonstration suite, and which 2+ published
  leakage results anchor the external reproduction tests.

The architecture is model-agnostic and detector-pluggable specifically so these
can be answered after scaffolding without rework: they only configure adapters,
detector presets, and the demonstration suite.
