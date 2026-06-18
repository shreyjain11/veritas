# Validation

Veritas separates two kinds of evidence, and reports them differently.

## What is validated now

The **engine and interfaces** are complete and validated by the test suite:

- Contracts, detectors, de-leaking, honest re-scoring, bootstrap CIs,
  stratification, and report assembly are covered by unit, property, and
  integration tests (the suite gates on ≥90% coverage; the project is at 100%).
- **Determinism** is asserted: reports are byte-identical on the pinned platform,
  and the `audit_hash` covers the full report.
- **Provenance** is asserted end-to-end, including the resolved detector binary
  path.
- Methodological limitations are **measured**, not assumed — the bootstrap
  coverage and prefilter-recall numbers on the
  [Limitations](limitations-and-guarantees.md) page come from tests in the suite.

## What is in progress

The **demonstration suite** and **external reproductions** are in progress
pending benchmark finalization:

- **Demonstration suite** — end-to-end audits on public benchmarks (e.g. a
  protein DMS task, a protein–protein interaction task using family/structural
  detectors, and a regulatory-DNA task).
- **External reproductions** — re-deriving published leakage findings with
  Veritas to show the auditor recovers known results.

!!! warning "No fabricated results"
    Until these datasets are finalized, **no demonstration or reproduction
    numbers are reported here.** This page will be updated with concrete results
    (and the configs/commands to reproduce them) once the benchmarks land. The
    absence of numbers is deliberate, not an omission.
