# CLAUDE.md — Veritas

> Project constitution. Read this fully at the start of every session. These are
> non-negotiable rules, not suggestions. When in doubt, choose correctness and
> provenance over speed or cleverness.

## What Veritas is

Veritas is a **model-agnostic, post-hoc leakage and robustness auditor for
sequence-based biological predictors.** You point it at (a) a benchmark
(sequences + labels + a declared split, or a model + its reference/training set)
and (b) a model's per-example predictions, and it produces a rigorous, fully
provenance-stamped audit:

1. **Cross-set contamination / leakage detection** — which evaluation items are
   too close to the model's training/reference set, under multiple notions of
   "close": sequence identity (homology), profile/family membership, and
   structural similarity. Each is a pluggable detector; an audit can use one or
   several.
2. **Reported-vs-honest metric** — the headline metric recomputed on the
   de-leaked evaluation set, with bootstrap confidence intervals and the delta.
3. **Stratified robustness ("silent failure" analysis)** — performance bucketed
   by difficulty axes (identity-to-nearest-train, alignment depth, label class)
   so you can see *where* a model quietly breaks even when its headline number
   looks fine.
4. **A report** — self-contained HTML + machine-readable JSON + Markdown, where
   **every single number is traceable** to its inputs, tool versions, and params.

It ships as a Python library, a CLI, and an **MCP server** so any agent can run
audits conversationally. It is **model-agnostic by construction** — no model,
benchmark, or organism is privileged. Utility is proven by a *demonstration
suite* spanning several distinct model/benchmark types (e.g. protein
variant-effect / fitness, protein function or interaction, and DNA/regulatory
sequence models), not by any single example.

## First principles (in priority order)

1. **Correctness over everything.** An auditor that is sometimes wrong is worse
   than useless — it launders false confidence. If a result cannot be validated,
   it does not ship.
2. **Validation-first / test-first.** No implementation code is written before a
   failing test that specifies it. Every module has a golden known-answer test.
3. **Provenance is mandatory.** No number is ever emitted without an attached
   provenance record (input content hashes, tool versions, params, seed). A
   report with an un-stamped number is a bug.
4. **Determinism.** Same inputs + same seed ⇒ byte-identical results and a stable
   provenance hash. Non-determinism is a defect to be hunted down, not tolerated.
5. **Model-agnostic by construction.** Core logic never imports or assumes any
   specific model, benchmark, or organism. Model/benchmark/reference specifics —
   and the choice of contamination detector(s) — live behind pluggable adapters
   only.
6. **Honest uncertainty.** Every metric is reported with a confidence interval.
   Never present a point estimate as if it were exact.

## The validation regime (non-negotiable)

Every phase must satisfy ALL of these before the next phase begins:

- **Unit tests** for every public function. Coverage gate: **≥ 90%** lines,
  fail CI below it.
- **Golden / injected-leakage tests.** Build synthetic datasets where YOU plant
  the leaked pairs and the true honest-metric delta, then assert the engine
  recovers them exactly. This is the backbone of correctness — you can prove the
  tool right because you know the answer.
- **Property-based tests (Hypothesis).** e.g. injecting a duplicate of a train
  item into the eval set must never *decrease* detected leakage; raising the
  identity threshold must be monotonic; de-leaking can only remove items.
- **Differential tests.** Cross-check homology calls against a reference
  mmseqs2/GraphPart run on a fixed dataset; assert agreement within tolerance.
- **External reproduction test.** Reproduce at least one *published* leakage
  finding end-to-end (e.g. a known protein-benchmark leakage result) and assert
  Veritas lands within stated tolerance. External validity, not just internal.
- **Determinism test.** Run twice; assert identical outputs + identical
  provenance hash.
- **Scale test.** Audit a 50k+ item benchmark within a documented time/memory
  budget.

Tests that are skipped, xfailed, or weakened to make CI green are a defect and
must be flagged explicitly to the user, never silently done.

## Stack (do not substitute without asking)

- Python 3.11+, managed with `uv` for the package; bioinformatics binaries
  (mmseqs2, optionally diamond) via micromamba/conda.
- `pytest`, `pytest-cov`, `hypothesis` — testing.
- `pydantic` v2 — all schemas, the prediction/benchmark/provenance contracts.
- `typer` — CLI. `mcp` (official Python SDK) — MCP server.
- `numpy`, `scipy`, `polars` (or pandas) — metrics + bootstrap.
- `datasketch` — MinHash pre-filter for scale.
- `matplotlib` — figures (self-contained SVG; no external JS chart libs).
- `ruff` (lint+format) + `mypy --strict` — both gate CI.
- `mkdocs-material` — docs. `hatchling` — packaging.

## How you work

- Use the ECC harness. For each phase: `tdd-workflow` skill (RED→GREEN→REFACTOR),
  then `/code-review`, then `/security-scan` where I/O or subprocess calls are
  touched, then `verification-loop` / `eval-harness` before declaring the phase
  done.
- Follow the phase plan in `docs/SPEC.md` strictly and in order. Do not start a
  phase until the previous phase's full test suite is green and coverage holds.
- Subprocess calls to mmseqs2/diamond must be sandboxed, input-validated, and
  version-pinned. Never shell-inject. Never trust file contents as commands.
- Never fabricate, hardcode, or "approximate" a scientific result, benchmark
  number, or expected value to make a test pass. If you don't have ground truth,
  build a synthetic case where you control it.
- Keep the core importable without the CLI or MCP layers present.
- Commit in small, reviewable units with conventional-commit messages. Each
  commit's tests pass.

## What "done" means for the whole project

Full test suite green; ≥90% coverage; mypy --strict and ruff clean; the
demonstration suite (≥3 distinct model/benchmark types, exercising sequence,
family, and structural contamination detectors) runs end-to-end from both the
CLI and the MCP server and produces identical reports both ways; the external
reproduction test(s) pass; docs build; CI is green on a clean checkout. Anything
less is not done.
