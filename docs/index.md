# Veritas

**Veritas** is a model-agnostic, post-hoc leakage & robustness auditor for
sequence-based biological predictors. It takes a model's predictions (already
computed), the evaluation sequences, and a reference set the model could have
memorized — and it answers one question honestly:

> How much of the reported performance survives once train/test leakage is
> removed?

Veritas never calls your model. It works on the predictions you hand it, so it
applies equally to a protein language model, a CNN on DNA, a docking score, or a
black-box API.

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
    The engine and interfaces are complete and validated by the test suite. The
    demonstration suite and external reproductions are in progress pending
    benchmark finalization — see [Validation](validation.md). No demonstration
    or reproduction results are reported until those land.

Start with [Usage](usage.md).
