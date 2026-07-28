# Veritas

A **model-agnostic benchmark-integrity auditor** for frontier-model evaluation
claims. Veritas tests whether reported benchmark performance transfers across
validated surface-form changes, fresh items, and available exposure controls. It
reports evidence and uncertainty—not accusations or an unsupported probability of
"cheating." The established sequence-based biological auditor remains available
as the legacy domain.

**[Run a browser audit](https://veritas-viewer.vercel.app/run) · [Website](https://veritas-viewer.vercel.app) · [Docs](https://veritas-viewer.vercel.app/docs) · [Report viewer](https://veritas-viewer.vercel.app/report)**

> **Status:** The legacy biological audit engine, its interfaces, **and the validation suite** are
> **complete** (comprehensive test coverage behind a ≥90% gate; `ruff`,
> `ruff format`, and `mypy --strict` all gate). Four demonstrations/reproductions —
> OverfitNN homology inflation (R3), genomic reverse-complement detection (R2),
> ProteinGym MSA-depth stratification, and PPI family + structural leakage
> detection — report **real, locked numbers on pinned data** (see
> [`docs/validation.md`](docs/validation.md); known edges and scoped future work
> are in [`docs/limitations-and-guarantees.md`](docs/limitations-and-guarantees.md)).
> No results are fabricated.

## Install

### Install from PyPI

```bash
python -m pip install "veritas-leakage[cli]"
```

For direct local open-weight inference, add the `local-model` extra. Named public
benchmark presets use the optional `benchmarks` extra:

```bash
python -m pip install "veritas-leakage[cli,local-model,benchmarks]"
veritas benchmarks
```

For development from a checkout, use `uv sync --extra cli` from the repository root.

The core package is dependency-light and importable without the optional layers;
the `cli` extra adds the `veritas` command, `mcp` exposes an MCP server, and `docs`
builds the documentation site. The detection backends (`mmseqs2`, `hmmer`,
`foldseek`) are external binaries — install them yourself (see
[Bioinformatics binaries](#bioinformatics-binaries)) or use the Docker image,
which bakes them in.

### Docker (detectors included, any OS)

```bash
docker pull ghcr.io/shreyjain11/veritas-leakage:latest
docker run --rm -v "$PWD:/work" ghcr.io/shreyjain11/veritas-leakage audit \
  --sequences /work/eval.fasta --table /work/table.csv \
  --reference /work/reference.fasta --config /work/config.json \
  --metric accuracy --out /work/report.json
```

The image bakes in the version-pinned detectors (`mmseqs2`, `diamond`, `foldseek`,
`hmmer`) plus the CLI, so it runs anywhere Docker does with no conda setup. Built
for `linux/amd64` (the platform the pinned binaries target).

## Benchmark-integrity quickstart

For the fastest hosted path, open the browser audit console. Choose one of eight
public multiple-choice benchmarks, select an allowlisted OpenAI-compatible provider,
and paste your own provider API key for that run. The key is sent over HTTPS, used
only in server request memory, cleared from the form, and excluded from caches,
logs, cookies, browser storage, and report provenance by Veritas. Hosted runs are
bounded to 20 parent items and 60 model requests; the UI shows the exact request
count and requires acknowledgement before transferring benchmark prompts.

The full CLI remains the path for private datasets, local model runtimes, larger
runs, resumable caching, and the complete detector suite.

Create a JSON (or YAML with the optional YAML dependency) audit specification pointing
to a JSONL benchmark and a model adapter, then inspect it before spending API budget:

```bash
veritas inspect --config audit.json
veritas audit --config audit.json --out audit-run/
```

The output package contains `report.json`, which opens in the schema-v2 report viewer.
For private benchmarks routed to an external endpoint, acknowledge the transfer explicitly:

```bash
veritas audit --config private-audit.json --out audit-run/ --acknowledge-external-transfer
```

See [`docs/BENCHMARK_INTEGRITY_SPEC.md`](docs/BENCHMARK_INTEGRITY_SPEC.md),
[`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md), and
[`docs/SCIENTIFIC_CLAIMS.md`](docs/SCIENTIFIC_CLAIMS.md) before interpreting findings.
For a direct local Transformers run, follow
[`docs/open-weight-models.md`](docs/open-weight-models.md).

Catalog-backed audits can select MMLU, MMLU-Pro, ARC-Challenge, OpenBookQA,
HellaSwag, CommonsenseQA, PIQA, WinoGrande, TruthfulQA, BoolQ, GPQA, HumanEval,
or SWE-bench Verified by name. The adapter records the upstream dataset,
configuration, split, revision, license, sampling window, and visibility in the
report. Use `veritas benchmarks <name>` to inspect a preset without downloading it.

## Legacy biological quickstart

A tiny, self-contained example ships in
[`examples/quickstart/`](examples/quickstart) — two of its four evaluation
sequences are exact duplicates of the reference set:

```bash
veritas audit \
  --sequences examples/quickstart/eval.fasta \
  --table     examples/quickstart/table.csv \
  --reference examples/quickstart/reference.fasta \
  --config    examples/quickstart/config.json \
  --metric    accuracy --out report.json
```

MMseqs2 finds the two memorized duplicates; the headline accuracy collapses from a
**reported 0.75** to an **honest 0.50** once they're removed, and the whole report
is signed with an `audit_hash`. Gate it in CI with `veritas gate --report
report.json --max-delta 0.05`. Full usage is in the
[documentation](https://veritas-viewer.vercel.app/docs).

## Development

```bash
# Python environment (uv-managed; Python pinned in .python-version)
uv sync

# Run the test suite with the coverage gate
uv run pytest

# Lint, format-check, and type-check
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

### Bioinformatics binaries

The contamination detectors shell out to version-pinned binaries (`mmseqs2`,
`diamond`, `foldseek`, `hmmer`) installed via conda/micromamba, not pip. To
provision them and add them to your `PATH`:

```bash
source scripts/setup-binaries.sh
```

The exact pins live in [`environment.yml`](environment.yml), and the resolved
binary path + version are recorded in every report's provenance.

## License

MIT — see [`LICENSE`](LICENSE).
