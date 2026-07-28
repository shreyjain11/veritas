# Veritas

**Veritas** is a model-agnostic benchmark-integrity auditor. It evaluates whether
frontier-model benchmark claims survive validated transformations and available
exposure controls, while naming uncertainty and alternative explanations.

> How robust is the reported benchmark score to meaningful changes in its surface
> form, evaluation protocol, and independently authored equivalents?

Veritas supports replay fixtures, closed API models, and compatible local endpoints.
The prior biological auditor is retained as a legacy domain.

## What it does

1. **Detects leakage** between evaluation items and the reference set using
   sequence-identity (MMseqs2), family (HMMER), and structural (Foldseek)
   detectors, combined into a single contamination graph.
2. **Re-scores honestly** — recomputes the metric on the de-leaked evaluation
   set, alongside the originally reported metric, each with a bootstrap
   confidence interval.
3. **Stratifies** performance by distance-to-nearest-reference so you can see
   the generalization gradient, not just a single number.
4. **Emits a signed report** (JSON / Markdown / HTML) whose every number carries
   provenance and is covered by an `audit_hash`.

## Design commitments

- **Model-agnostic by construction** — predictions in, audit out.
- **Provenance on every number** — see [Limitations & guarantees](limitations-and-guarantees.md).
- **Deterministic** — byte-identical reports on the pinned platform.
- **Honest about uncertainty** — bootstrap CIs and disclosed limitations travel
  inside the report (and are hashed into it).

!!! note "Validation status"
    The engine, interfaces, and the **validation suite** are complete: four
    demonstrations/reproductions report real, locked numbers on pinned data — see
    [Validation](validation.md). Known edges and scoped future work are listed under
    [Limitations & guarantees](limitations-and-guarantees.md). No results are fabricated.

Start with [Usage](usage.md).
