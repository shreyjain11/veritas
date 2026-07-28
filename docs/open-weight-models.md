# Auditing an open-weight model

Install the local inference and benchmark-catalog extras from PyPI:

```bash
python -m pip install "veritas-leakage[cli,local-model,benchmarks]"
```

Alternatively, from the repository root, run
`uv sync --extra cli --extra local-model --extra benchmarks` and prefix the
commands below with `uv run`.

List the built-in catalog without downloading benchmark data:

```bash
veritas benchmarks
veritas benchmarks mmlu
```

The included `catalog_open_weight_audit.json` runs a deterministic 100-item MMLU
window through the same prompt, transformation, detector, statistics, cache, and
report pipeline:

```bash
veritas inspect --config examples/benchmark_integrity/catalog_open_weight_audit.json
veritas audit \
  --config examples/benchmark_integrity/catalog_open_weight_audit.json \
  --out runs/mmlu-qwen/
```

Inspect the included four-item multiple-choice audit before loading the model:

```bash
veritas inspect --config examples/benchmark_integrity/open_weight_audit.json
```

Run it:

```bash
veritas audit \
  --config examples/benchmark_integrity/open_weight_audit.json \
  --out runs/open-weight-smoke/
```

The first run downloads the declared Hugging Face model and stores responses in the configured content-addressed cache. Re-running the same model revision, system prompt, item, generation settings, and adapter version reuses those observations. Changing any of them produces a new cache key.

Open `runs/open-weight-smoke/report.json` in the website's v2 viewer. It exposes canonical prompts, choices, expected and parsed answers, raw generations, correctness, transformed-item lineage, latency, token counts, likelihood availability, aggregate scores, paired confidence intervals, and detector findings.

## Interpretation

Generated-token log probabilities are recorded when the model runtime supplies them. The initial probability summary is deliberately uncalibrated and does not establish training membership. A defensible exposure analysis still requires matched controls or known member/non-member validation data.

The example is an execution smoke test, not a scientific benchmark claim. Replace the JSONL file with the audited benchmark and pin a model revision whenever the upstream repository exposes a stable revision.
