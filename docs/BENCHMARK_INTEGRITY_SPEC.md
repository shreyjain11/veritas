# Veritas v2: benchmark integrity

Veritas v2 audits evidence about benchmark integrity; it does not determine intent or claim a model is contaminated from a score drop alone. An audit records canonical, transformed, and optional fresh/temporal performance alongside detector-specific assumptions, alternatives, uncertainty, and provenance.

The v2 root contracts are `BenchmarkItem`, `Benchmark`, `ModelTarget`, `ModelResponse`, `Transformation`, `DetectorFinding`, and schema-versioned `AuditReport`. The pipeline is load → validate → canonical evaluation → transformations → transformed evaluation → detectors → aggregation → report. Optional requirements produce `not_run`, never silent omission.

## Initial workflow

```bash
veritas inspect --config audit.json
veritas audit --config audit.json --out audit-run/
```

Use `--acknowledge-external-transfer` only when a private benchmark is intentionally sent to a configured external endpoint.

## Transformations

Every transformation is a pure function of the parent item and a seed, and records its
lineage (`parent_item_id`, `child_item_id`, the child's answer key, parameters, and a
content hash). Variants that do not apply, or that would present an identical prompt, are
skipped rather than counted.

| family | what changes | validation |
| --- | --- | --- |
| `choice_permutation` | option texts move under fixed positional labels; the correct answer always moves | valid (uncertain if two options share a text) |
| `choice_label_remap` | labels become a fresh bijective scheme (numerals or unused letters) | valid |
| `formatting` | prompt template and whitespace layout; task text and options unchanged | valid |
| `identifier` | placeholder identifiers are renamed consistently (`x`→`beta`, `y`→`gamma`) | uncertain — excluded from the robust score |

Answers are parsed once, the same way for every adapter: explicit statements ("The answer
is B", "Answer: (B)", `**C**`) and restated option text map to a label; output that names
no single option parses to `null` and is scored as wrong. Missing or errored responses are
excluded from scores and paired comparisons, never counted as wrong.

## Decision rule

Paired detectors (`perturbation`, `option_order`, `template_dependence`) compare each parent
item's canonical correctness with its mean correctness across validated variants. They report
the paired gap, a percentile-bootstrap 95% interval, a sign-flip permutation p-value, and a
Benjamini-Hochberg-corrected p-value across all tested findings. The verdict is:

- **supports** (weak indirect) — gap > 0, interval lower bound > 0, and corrected p ≤ `alpha` (0.05);
- **contradicts** (against) — interval upper bound < `equivalence_margin` (0.05): any drop is smaller than the margin;
- **inconclusive** — otherwise, or with fewer than `min_parent_items` (10) paired items.

Each threshold can be overridden per detector, e.g. `{"type": "option_order", "config": {"min_parent_items": 20}}`.
The evidence matrix maps each hypothesis to the detectors that bear on it, lists supporting,
contradicting, and unavailable detectors, and reports the strongest supporting strength.

## Integrity hash

`audit_hash` is the SHA-256 of the canonical JSON of the entire report except the hash itself
(sorted keys, compact separators, ASCII escaping, integer-valued numbers as integers, other
numbers in Python float `repr`). The TypeScript viewer reproduces it byte for byte, so `veritas
verify` and the web viewer both detect any edit made after signing.
