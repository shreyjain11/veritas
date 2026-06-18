# Veritas — File-Level Implementation Plan

> Companion to `CLAUDE.md` (constitution) and `docs/SPEC.md` (architecture). This
> document plans *how* each gated phase in SPEC §6 is built and *which tests*
> (per the validation regime in SPEC §5) gate each phase. No implementation code
> is written until a failing test specifies it (CLAUDE.md first principle #2).
>
> **Status:** plan approved with the decisions recorded in §0.5. Phase 0 is NOT
> started — awaiting explicit "go".

---

## 0. Project-wide conventions

- **Layout:** `src/`-layout (`src/veritas/...`) so tests run against the
  installed wheel — this is what makes the "core imports without cli/mcp" rule
  (SPEC §3 hard rule) and the clean-checkout gate testable.
- **Packaging:** `hatchling`, deps managed by `uv`, lockfile committed. Import/
  repo name is `veritas`; PyPI distribution name (e.g. `veritas-audit`) is chosen
  and availability-checked at Phase 8. License: **MIT**.
- **Optional-dependency groups:** `cli` (typer), `mcp` (mcp SDK), `docs`
  (mkdocs-material), `dev` (pytest/hypothesis/ruff/mypy/coverage + **scikit-learn,
  test-only**). Core install pulls none of `cli`/`mcp`/sklearn.
- **DataFrames:** **polars internally.** IO accepts CSV/TSV/parquet and converts
  to polars at the boundary; polars is never exposed in public contracts.
- **Binaries** come from conda/micromamba (channels **conda-forge + bioconda**),
  pinned in `environment.yml` — never pip. Pins: `mmseqs2=18.8cc5c`,
  `diamond=2.2.1`, `foldseek=10.941cd33`, `hmmer=3.4`.
- **Python:** CI matrix **3.11–3.13**. The determinism gate runs on a single
  pinned version (**3.12**).
- **Determinism contract:** byte-identical outputs + stable `audit_hash` on the
  pinned CI platform with fixed seeds and all floats routed through one canonical
  serializer (fixed precision). **No cross-arch guarantee.** SVG figures stripped
  of nondeterministic metadata.
- **Cache:** `$XDG_CACHE_HOME/veritas` (default `~/.cache/veritas`), overridable
  by env/config; project-local cache is opt-in. **CI unit tests run clean-cache.**
- **Network policy:** the core suite (unit / golden / property / differential) is
  fully hermetic/offline on vendored fixtures. Every network-touching test
  (full Pfam-A, AlphaFold-DB, external-repro datasets) lives in an **opt-in job
  that never gates core CI**.
- **pytest markers:** `requires_mmseqs`, `requires_diamond`, `requires_foldseek`,
  `requires_hmmer`, `requires_pfam`, `slow`, `scale`, `external`. Binary-gated
  tests auto-skip locally when the binary is absent and run for real in CI.
  **Skips never count toward coverage and are surfaced, never silent.**
- **Coverage gate:** **90%** lines, authoritative. **Precedence rule (baked in):
  `CLAUDE.md` and `docs/SPEC.md` override the generic ECC rule files
  (`.claude/rules/ecc/**`) wherever they conflict** — e.g. the 90% gate here wins
  over the 80% in `testing.md`. This precedence is documented in `README.md` and
  the contributing notes.
- **Shared test infrastructure** (built early, reused everywhere):
  - `tests/conftest.py` — seeded-RNG fixture, tmp/clean cache dir, binary-skip
    logic, canonical-compare helpers.
  - `tests/factories.py` — backbone of the golden suite:
    `make_eval_set_with_planted_leakage()`, `make_inflation_construction()`
    (contamination correlated with correctness, known reported−honest delta),
    `make_specificity_control()` (contamination *uncorrelated* with correctness —
    requirement A), `make_failure_regime()` (performance monotone in a difficulty
    axis), `make_edge_cases()` (requirement B).
  - `tests/fixtures/` — small committed artifacts: sample FASTA (protein +
    nucleotide), CSV/TSV/parquet prediction tables, *captured* tool output (for
    parser tests needing no binary), a tiny curated HMM set, a few small PDB/mmCIF
    structures, golden reports.

---

## 0.5 Resolved decisions (approved)

| # | Decision | Resolution |
|---|---|---|
| 1 | Layout | `src/veritas/` src-layout |
| 2 | DataFrames | polars internally; IO accepts CSV/TSV/parquet and converts |
| 3 | Metrics deps | hand-roll in numpy/scipy; **scikit-learn test-only** as differential reference for the metric impls (Hypothesis edge cases: ties, single-class); runtime stays sklearn-free |
| 4 | Report templating | jinja2 for HTML/MD |
| 5 | Family backend | pyhmmer confirmed; vendor a tiny curated HMM set as offline fixtures; full Pfam-A = pinned release, fetched on demand into cache, content-hash verified, **opt-in integration/demo job only**, never unit CI |
| 6 | Structures | user-provided PDB/mmCIF is the primary path; vendor small structures for tests; structural golden = controlled coordinate perturbation of a known structure; AlphaFold-DB fetch = optional demo-only adapter; **no ESMFold dependency** |
| 7 | diamond | runtime-optional (skip-if-absent); CI installs + pins + runs its differential test |
| 8 | Binary pins | conda-forge + bioconda: `mmseqs2=18.8cc5c`, `diamond=2.2.1`, `foldseek=10.941cd33`, `hmmer=3.4` |
| 9 | Predictions + metrics | v1 = scalar per item (binary score / regression / ranking); metrics = AUROC, AUPRC, Spearman, Pearson, + thresholded accuracy/MCC/F1 when labels binary; contract kept **vector-ready** (multiclass/multilabel deferred, non-breaking) |
| 10 | De-leak policies | ship all three; default = **drop**; `reweight` documents its weighting scheme + carries own property tests; `stratify` shares Phase 4 machinery |
| 11 | Demo suite | **PROVISIONAL (confirm tomorrow):** ProteinGym DMS (sequence); a PPI/function benchmark (family + structural); a regulatory-DNA task (nucleotide) |
| 12 | External repro | **PROVISIONAL:** #1 protein-interaction homology leakage (arXiv 2404.10457); #2 genome-trained cross-chromosome leakage (hashFrag); tolerances set once datasets fixed |
| 13 | Determinism scope | byte-identical on pinned CI platform; floats canonicalized in serialization; seeds fixed; no cross-arch guarantee |
| 14 | Coverage + precedence | 90% authoritative; CLAUDE.md/SPEC.md override generic ECC rule files on conflict |
| 15 | Scale | CI: **10k×10k** within a committed ceiling on the runner; separate opt-in benchmark: **50k×50k** within a committed time/mem budget on **n2-standard-16**; ceilings committed, numbers tunable |
| 16 | Structural prefilter | skip MinHash; use foldseek's own prefilter |
| 17 | Cache | `$XDG_CACHE_HOME/veritas` (default `~/.cache/veritas`), env/config overridable, project-local opt-in; CI unit tests clean-cache |
| 18 | Name + license | import/repo `veritas`; PyPI under distinct name (e.g. `veritas-audit`) at Phase 8; MIT |
| 19 | Python | CI 3.11–3.13; determinism gate on 3.12 |
| 20 | Network | core suite hermetic/offline; network tests in opt-in job, never gate core CI |
| 21 | MCP | stdio v1; server structured so HTTP/SSE can be added without touching tool logic |
| 22 | Alphabets | protein + nucleotide from the start (contracts/IO/sequence detector); family + structural detectors are **protein-only** — validate and raise a clear error on nucleotide input |

---

## 1. The three-detector common interface (confirmed)

All three backends sit behind one interface — the spine of SPEC §3's
`contamination/` module.

```
ContaminationDetector            (abstract; src/veritas/contamination/base.py)
  .kind: DetectorKind            # SEQUENCE | FAMILY | STRUCTURE
  .supported_alphabets           # SEQUENCE: {protein, nucleotide};
                                 # FAMILY, STRUCTURE: {protein} only
  .params_schema: type[BaseModel]
  .detect(eval_items, reference_items, params) -> ContaminationGraph
        # edges: (eval_id, ref_id, score, kind, detector_id, params_hash)

  ├─ SequenceIdentityDetector    sequence_identity.py  → mmseqs2 (primary),
  │                                                       diamond (optional)
  ├─ FamilyDetector              family.py             → pyhmmer + Pfam (in-process)
  └─ StructuralDetector          structural.py         → foldseek
```

Everything downstream (metrics, de-leak, stratify, report) consumes the **same**
`ContaminationGraph`, so it is entirely detector-agnostic. Shared infrastructure:

- `prefilter.py` — MinHash/LSH candidates (datasketch) for the sequence/family
  backends. **Structural skips this and uses foldseek's own prefilter** (#16).
- `subprocess_runner.py` — single sandboxed exec path for mmseqs2 / diamond /
  foldseek (arg-list only, never `shell=True`, temp-dir isolation, timeout,
  runtime version capture). pyhmmer runs in-process, so its safety boundary is
  Pfam-DB integrity + input validation, not subprocess sandboxing.
- `cache.py`, `registry.py`, `compose.py` (union/intersect).

**Alphabet rule (#22):** the sequence detector supports protein + nucleotide;
the family and structural detectors are protein-only and raise a clear,
typed error (not a crash) when handed nucleotide input.

---

## 1.5 Cross-cutting requirements A–C

These are first-class and threaded into specific phases below.

- **A — Specificity twins.** Every "detects inflation" golden is paired with a
  "no false inflation" twin built by `make_specificity_control()`: contamination
  present but **uncorrelated** with correctness ⇒ honest ≈ reported within CI
  (the engine must not invent a gap). The same principle extends to detectors
  (no spurious edges among unrelated items) and stratification (flat true
  performance ⇒ no false silent-failure flag).
- **B — Edge-case suite.** Explicit, asserted behavior for: zero contamination
  (`honest == reported`); total contamination (de-leaked set empty ⇒ an explicit
  **"insufficient clean data"** result status — no NaN, no crash); single-class
  labels (AUROC/AUPRC return an explicit "undefined" status, not NaN); score
  ties (deterministic, documented tie handling). This requires a result-status
  enum in the contracts (Phase 1) that the metrics, de-leak, report, CLI, and
  MCP layers all honor.
- **C — Runtime provenance.** `ProvenanceRecord` carries **both** the pinned
  config versions and the **runtime-captured** backend version strings
  (`mmseqs version`, `foldseek version`, `hmmsearch -h`, `diamond version`)
  obtained by invoking the tool during the run. A pinned-vs-runtime mismatch is
  surfaced as an explicit warning flag in the manifest, never silently dropped.

---

## 2. Phase 0 — Scaffold

**Goal:** repo builds, tooling gates run, one *failing* smoke test exists.

### Files
- `pyproject.toml` — hatchling; deps + optional groups (incl. test-only sklearn);
  tool config for ruff, mypy (`strict = true`), pytest, coverage (`fail_under=90`).
- `.python-version`, `uv.lock`, `.gitignore`, `LICENSE` (MIT), `README.md`
  (states the CLAUDE.md/SPEC.md-over-ECC precedence rule).
- `environment.yml` — conda-forge + bioconda; the four pinned binaries.
- `src/veritas/__init__.py` (`__version__`), `src/veritas/py.typed`.
- `tests/__init__.py`, `tests/conftest.py` (skeleton), `tests/test_smoke.py`.
- `.github/workflows/ci.yml` — uv sync; micromamba binaries (pinned); ruff;
  `mypy --strict`; pytest+coverage gate; 3.11–3.13 matrix; determinism gate on
  3.12; clean-cache for unit tests; network/opt-in jobs separated.

### Tests
- `test_smoke.py::test_version_importable` — RED first → GREEN after scaffold.
- `tests/test_import_isolation.py` — importing core `veritas` must not import
  `typer`, `mcp`, or `sklearn` (checked via `sys.modules`). Kept green every phase.

### Gate
Smoke + isolation green; ruff/mypy clean; CI runs end-to-end.

---

## 3. Phase 1 — Contracts + IO + Provenance

**Goal:** every data shape is a validated pydantic v2 model; loaders deterministic;
provenance hashing stable and proven deterministic.

### Files — `src/veritas/contracts/`
- `enums.py` — `SeqType` (protein/nucleotide), `DetectorKind`, `DeLeakPolicy`,
  `CombinePolicy`, `MetricName`, **`ResultStatus`** (ok / insufficient_clean_data
  / undefined_metric — requirement B).
- `eval_item.py` — `EvalItem` (id, sequence, label, prediction, metadata), frozen,
  alphabet-validated by `SeqType`.
- `reference_item.py` — `ReferenceItem` (id, sequence, optional structure path,
  "why seen" provenance).
- `predictions.py` — `PredictionRecord`/`PredictionSet`; **scalar value in v1 but
  shape kept vector-ready** so multiclass/multilabel is a non-breaking addition.
- `benchmark.py` — `Benchmark` (eval items + `SplitSpec` + metric spec).
- `audit_config.py` — `AuditConfig` + `DetectorConfig` (identity/coverage, family
  E-value, structural TM/score), de-leak policy (default drop), bootstrap n, seed,
  stratification axes, tool choices/versions.
- `contamination.py` — `ContaminationEdge`, `ContaminationGraph`.
- `provenance.py` — `ProvenanceRecord`: input hashes, params, seed, timestamps,
  **`pinned_versions` + `runtime_versions` + `version_mismatch_flags`** (req C).
- `report.py` — `AuditReport`, `TracedValue` (number bound to a provenance ref),
  carries `ResultStatus` so "insufficient clean data" / "undefined" render
  cleanly.

### Files — `src/veritas/io/`
- `fasta.py` (protein + nucleotide), `predictions_io.py` (CSV/TSV/parquet →
  polars), `splits.py` — deterministic loaders.
- `adapters.py` — `BenchmarkAdapter`/`ModelAdapter`/`ReferenceAdapter` Protocols
  (only place model/benchmark specifics may live, per principle #5).
- `loaders.py` — assemble a `Benchmark` from files.

### Files — `src/veritas/provenance/`
- `canonical.py` (canonical JSON, fixed float format), `hashing.py` (sha256 over
  canonical form), `tool_versions.py` (runtime capture interface; mocked here,
  real in Phase 2), `record.py`, `audit_hash.py`.

### Tests
- **Unit:** `tests/contracts/test_*` (validation, frozen, round-trip, alphabet
  acceptance for both protein and nucleotide, `ResultStatus` round-trip);
  `tests/io/test_fasta.py` (golden parse, malformed rejected, deterministic order,
  protein + nucleotide); `tests/io/test_predictions_io.py` (CSV/TSV/parquet all
  load to the same polars frame); `tests/io/test_splits.py`,
  `tests/io/test_adapters.py`.
- **Golden hash:** `tests/provenance/test_hashing.py` — fixed input → committed
  expected hash; one-byte change flips it.
- **Property (Hypothesis):** `tests/provenance/test_canonical.py` —
  serialize→parse→serialize idempotent; any permutation of unordered collections
  → identical content hash.
- **Determinism:** `tests/provenance/test_audit_hash.py` — same inputs ⇒ identical
  hash twice; seed/param change ⇒ different hash.
- **Req C scaffolding:** `tests/provenance/test_versions.py` — record carries both
  pinned and runtime version slots; a pinned≠runtime mismatch sets a flag (runtime
  side mocked here).

### Gate
All green; ≥90%; hashing determinism proven; import-isolation green.

---

## 4. Phase 2 — Contamination engine (the heart)

**Goal:** the common interface + all three backends + prefilter + cache +
composition, validated by planted ground truth and against the real tools, with
runtime provenance captured.

### Files — `src/veritas/contamination/`
- `base.py` (interface + `DetectorResult` + alphabet guard), `graph.py`,
  `prefilter.py`, `cache.py`, `subprocess_runner.py`, `registry.py`, `compose.py`.
- `sequence_identity.py` (mmseqs2 primary, diamond optional; protein + nucleotide),
  `family.py` (pyhmmer + Pfam; protein-only guard),
  `structural.py` (foldseek; protein-only guard; user PDB/mmCIF).
- `backends/mmseqs.py`, `backends/diamond.py`, `backends/foldseek.py`,
  `backends/pfam.py` — thin run+parse wrappers; **parsers tested independently of
  the binary** via committed fixtures; each backend also exposes a runtime
  `version()` call (req C).

### Tests
- **Golden injected-contamination (one per detector) — the cornerstone:**
  - `test_sequence_golden.py` — eval planted as exact dups / known-% mutants of
    ref + unrelated decoys; exact edge recovery at threshold, **zero spurious
    edges** (specificity, req A), correct threshold sensitivity; protein AND
    nucleotide variants.
  - `test_family_golden.py` — eval planted into the same family as ref + a
    different-family decoy (vendored tiny HMM set); family edges recovered;
    nucleotide input raises the typed protein-only error.
  - `test_structural_golden.py` — eval = coordinate-perturbed copy of a vendored
    ref structure + an unrelated fold; edges above TM threshold; nucleotide/
    no-structure inputs error cleanly.
- **Differential (per backend, vs pinned reference run — SPEC §5.4):**
  - `test_sequence_differential.py` — vs pinned raw `mmseqs2` and (when present)
    `diamond`; edge set + identities within tolerance. `requires_mmseqs` /
    `requires_diamond`.
  - `test_family_differential.py` — pyhmmer vs pinned `hmmsearch`/`hmmscan`.
    `requires_hmmer` (vendored HMMs; full Pfam-A only in the opt-in job).
  - `test_structural_differential.py` — vs pinned `foldseek`. `requires_foldseek`.
- **Property (Hypothesis) — `test_properties.py`:** duplicate-in-eval never
  decreases edges; threshold monotonicity; `union ⊇ inputs ⊇ intersect`; MinHash
  candidate set never drops a planted near-duplicate above the configured Jaccard;
  same input + seed ⇒ identical graph.
- **Unit:** `test_prefilter.py`, `test_cache.py` (2nd call hits cache, backend
  call-count 0), `test_graph.py`, `test_registry.py` (all three registered, share
  interface, alphabet support declared), `test_backends_parsers.py` (fixture
  output → expected hits, no binary).
- **Security:** `test_subprocess_runner.py` — never `shell=True`, rejects
  metacharacter injection, validates inputs, honors timeout, never executes file
  contents. Backed by a `/security-scan` pass.
- **Req C:** `test_runtime_versions.py` — running a detector populates
  `runtime_versions` with the real tool strings; mismatch vs `pinned_versions`
  raises the manifest flag. `requires_*` per backend.

### Gate
All green; differential within tolerance; security review passed; runtime
versions captured; ≥90%.

---

## 5. Phase 3 — Metrics + de-leak

**Goal:** metric registry + bootstrap CIs + all three de-leak policies +
reported-vs-honest delta with CI, with specificity twins and edge cases.

### Files — `src/veritas/metrics/`
- `registry.py` (name → metric + task-type guard).
- `auroc.py`, `auprc.py`, `correlation.py` (Spearman/Pearson via scipy),
  `classification.py` (thresholded accuracy/MCC/F1, binary only) — **numpy/scipy
  only, runtime sklearn-free**.
- `bootstrap.py` (seeded resampling, percentile + BCa).
- `deleak.py` — `drop` (default) / `stratify` / `reweight`; `reweight` documents
  its weighting scheme inline.
- `honest.py` — reported vs honest, delta, paired-bootstrap CI for the delta;
  emits `ResultStatus.insufficient_clean_data` when the de-leaked set is empty.

### Tests
- **Golden:**
  - `test_metrics_golden.py` — hand-computed AUROC/AUPRC/Spearman/Pearson/MCC/F1
    on tiny vectors (perfect/reversed/tied) → exact known answers.
  - `test_honest_golden.py` — inflation construction: planted reported−honest
    delta recovered exactly.
  - `test_deleak_golden.py` — `drop` removes exactly the contaminated items;
    `reweight` yields known weights; `stratify` partitions correctly.
- **Specificity twin (req A):** `test_honest_specificity.py` —
  `make_specificity_control()`: contamination uncorrelated with correctness ⇒
  `honest ≈ reported` within CI (no invented gap).
- **Edge cases (req B):** `test_metrics_edge_cases.py` — zero contamination ⇒
  `honest == reported`; total contamination ⇒ `insufficient_clean_data` (no NaN,
  no crash); single-class labels ⇒ `undefined_metric` for AUROC/AUPRC; score ties
  handled deterministically.
- **Differential (test-only sklearn, req #3):** `test_metrics_differential.py` —
  our AUROC/AUPRC/Spearman/Pearson/MCC/F1 vs scikit-learn on random + Hypothesis
  edge inputs (ties, single-class, all-equal scores) within tolerance.
- **Property (Hypothesis) — `test_properties.py`:** de-leak only removes; `drop`
  idempotent; honest ≤ reported under the inflation construction; bootstrap CI
  covers the planted value at ≈ nominal rate; AUROC/Spearman invariant under
  monotone score transforms; `reweight` has its own invariant tests (uniform
  weights ⇒ equals unweighted metric; zero weight on an item ⇒ equals dropping it).
- **Unit:** `test_bootstrap.py` (determinism, width shrinks with n),
  `test_registry.py` (unknown metric errors, task-type guard).

### Gate
All green; specificity + edge cases pass; sklearn differential within tolerance;
≥90%.

---

## 6. Phase 4 — Stratification

**Goal:** difficulty axes + performance-vs-difficulty curves + silent-failure
flagging, with a specificity twin.

### Files — `src/veritas/stratify/`
- `axes.py` (identity-to-nearest-ref per detector from the graph; alignment/
  structure depth; label class), `binning.py` (fixed + quantile, deterministic),
  `curves.py` (per-bucket metric + CI, reusing Phase 3 bootstrap),
  `silent_failure.py` (flag buckets below aggregate despite healthy headline).

### Tests
- **Golden:** `test_stratify_golden.py` — `make_failure_regime()`: known curve
  shape recovered; low-identity bucket flagged. `test_axes_golden.py` —
  identity-to-nearest-ref from a known graph matches hand values.
- **Specificity twin (req A):** `test_stratify_specificity.py` — flat true
  performance across the axis ⇒ no false silent-failure flag.
- **Edge cases (req B):** empty bucket / single-class bucket handled via
  `ResultStatus` rather than NaN.
- **Property:** buckets partition the eval set exactly (counts sum to total, no
  double-count); monotone-constructed performance ⇒ monotone recovered curve
  within CI.
- **Unit:** `test_binning.py` (quantile/fixed determinism).

### Gate
All green; planted regime recovered; specificity holds; ≥90%.

---

## 7. Phase 5 — Report

**Goal:** self-contained HTML + JSON + Markdown; every number traceable and
agreeing across formats; status results render cleanly.

### Files — `src/veritas/report/`
- `model.py` (assemble `AuditReport` from pipeline outputs; uses `TracedValue` +
  `ResultStatus`), `json_report.py`, `markdown_report.py`, `html_report.py`
  (jinja2; inline CSS + inline SVG, **no external JS/CDN**), `figures.py`
  (matplotlib SVG, determinism-stripped), `numbers.py` (TracedValue helper),
  `templates/` (jinja2 HTML/MD).

### Tests
- **Snapshot:** `test_snapshot_json.py` / `_md.py` / `_html.py` — fixed report →
  committed golden (canonical byte-compare for JSON/MD; structural assertions for
  HTML).
- **Cross-format number agreement (SPEC §5.8):** `test_cross_format_numbers.py` —
  every numeric token in JSON/MD/HTML matches exactly.
- **Provenance completeness (principle #3):** `test_provenance_completeness.py` —
  no number renders without a provenance ref; manifest includes runtime versions
  (req C) and any mismatch flags.
- **Edge-case rendering (req B):** `test_report_status_rendering.py` —
  "insufficient clean data" / "undefined metric" render as explicit, readable
  states (no `NaN`, no blank).
- **Self-containment:** `test_html_self_contained.py` — no external resource refs.
- **Determinism:** `test_figures.py` — render twice → identical SVG.

### Gate
All green; cross-format numbers agree; HTML self-contained; ≥90%.

---

## 8. Phase 6 — CLI + demonstration suite

**Goal:** one orchestrator drives CLI (now) and MCP (Phase 7); ≥3 distinct
model/benchmark types run end-to-end exercising all detectors; published findings
reproduced.

### Files — `src/veritas/audit/`
- `orchestrator.py` — `run_audit(config, inputs) -> AuditReport`, provenance
  stamped throughout. **Single source of truth for CLI and MCP.**
- `pipeline_steps.py` — `detect` / `rescore` / `stratify` independently callable.

### Files — `src/veritas/cli/`
- `app.py` (typer entrypoint `veritas`), `commands/audit.py`, `commands/leakage.py`,
  `commands/rescore.py`, `commands/stratify.py`, `io_helpers.py`.

### Demonstration + external reproduction
- `demos/` — pinned config + data-fetch manifests for the three **provisional**
  types (#11): ProteinGym DMS (sequence), a PPI/function benchmark (family +
  structural), a regulatory-DNA task (nucleotide). Large data fetched, not
  committed; the optional AlphaFold-DB adapter lives here.
- `tests/e2e/test_demo_*.py` — each demo runs end-to-end (`external`/opt-in).
- `tests/e2e/test_external_repro_protein.py` (arXiv 2404.10457),
  `tests/e2e/test_external_repro_genomic.py` (hashFrag cross-chromosome) —
  reproduce within tolerance fixed once datasets land (#12); `external`/opt-in.
- `tests/cli/test_cli_audit.py`, `tests/cli/test_cli_subcommands.py` — typer
  `CliRunner`; outputs, exit codes, arg validation, `ResultStatus` exit behavior.
- `tests/scale/test_scale_10k.py` — **10k×10k within a committed ceiling on the
  CI runner** (`scale`/`slow`).
- `tests/scale/test_scale_50k.py` — **50k×50k within a committed time/mem budget
  on n2-standard-16** (`scale`/opt-in); ceilings committed, numbers tunable.

### Gate
All green; demos + external repro pass in the opt-in job; 10k scale ceiling met
in CI; ≥90%.

---

## 9. Phase 7 — MCP server

**Goal:** expose the audit over MCP (stdio); prove the agent path equals the CLI
path byte-for-byte.

### Files — `src/veritas/mcp/`
- `server.py` — official MCP SDK, **stdio transport**, structured so HTTP/SSE can
  be added without touching tool logic (#21). Tools: `detect_leakage`, `rescore`,
  `stratify`, `run_audit`, `get_provenance`.
- `tools.py` — pydantic tool schemas + handlers calling `audit/` (no logic
  duplicated from the CLI).
- `serialization.py` — `AuditReport` ↔ MCP result.

### Tests
- `tests/mcp/test_cli_mcp_parity.py` — **headline parity:** same audit via CLI and
  via MCP ⇒ identical `AuditReport` + identical `audit_hash`.
- `tests/mcp/test_tools.py` — each handler returns a valid result for a fixture.
- `tests/mcp/test_server_smoke.py` — server starts, lists tools, validates schemas.

### Gate
All green; CLI≡MCP parity proven; ≥90%.

---

## 10. Phase 8 — Polish

**Goal:** ship-ready.

### Files
- `action.yml` / `.github/workflows/audit-action.yml` — CI-droppable audit Action.
- `mkdocs.yml` + `docs/` pages (index, usage, detectors, validation, API).
- `CHANGELOG.md`; final packaging (entry points, classifiers, PyPI name
  availability check + set).

### Tests
- `tests/docs/test_docs_build.py` — mkdocs build succeeds.
- `tests/test_packaging.py` — wheel builds; entry points present; **core imports
  without cli/mcp/sklearn extras** (extends Phase-0 isolation).
- Clean-checkout CI job — full suite green from scratch with pinned binaries.

### Gate
Everything in CLAUDE.md "What done means" satisfied.

---

## 11. Validation-regime coverage map (SPEC §5 + reqs A–C → where it lives)

| Regime / requirement | Where |
|---|---|
| Unit + ≥90% coverage | every phase, CI `fail_under=90` |
| Golden injected-leakage | Phase 2 (per detector), Phase 3 (inflation), Phase 4 (failure regime) |
| **A — specificity twins** | Phase 3 (`test_honest_specificity`), Phase 4 (`test_stratify_specificity`), Phase 2 (zero-spurious-edge asserts) |
| **B — edge-case suite** | `ResultStatus` in Phase 1; Phase 3 (`test_metrics_edge_cases`); Phase 4 (empty/single-class buckets); Phase 5 (status rendering) |
| **C — runtime provenance** | schema Phase 1; capture + mismatch flag Phase 2; manifest render Phase 5 |
| Property-based (Hypothesis) | Phases 1–4 (`test_properties.py` each) |
| Differential vs backends | Phase 2 (mmseqs/diamond, hmmer/Pfam, foldseek); Phase 3 (metrics vs test-only sklearn) |
| External reproduction | Phase 6 (`tests/e2e/test_external_repro_*`, opt-in) |
| Determinism | Phase 1 (hash), Phase 5 (SVG/report), Phase 7 (CLI≡MCP); gate on 3.12 |
| Scale | Phase 6 (10k×10k CI, 50k×50k opt-in on n2-standard-16) |
| Report snapshot + cross-format | Phase 5 |
