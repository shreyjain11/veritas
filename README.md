# Veritas

A **model-agnostic, post-hoc leakage & robustness auditor** for sequence-based
biological predictors. Point it at a benchmark (sequences + labels + a declared
split, or a model + its reference set) and a model's per-example predictions, and
it produces a rigorous, fully provenance-stamped audit: cross-set contamination
detection, the reported-vs-honest metric on the de-leaked set, and a stratified
"silent failure" analysis.

**[Website](https://veritas-viewer.vercel.app) · [Docs](https://veritas-viewer.vercel.app/docs) · [Report viewer](https://veritas-viewer.vercel.app/report)**

> **Status:** The audit engine, its interfaces, **and the validation suite** are
> **complete** (comprehensive test coverage behind a ≥90% gate; `ruff`,
> `ruff format`, and `mypy --strict` all gate). Four demonstrations/reproductions —
> OverfitNN homology inflation (R3), genomic reverse-complement detection (R2),
> ProteinGym MSA-depth stratification, and PPI family + structural leakage
> detection — report **real, locked numbers on pinned data** (see
> [`docs/validation.md`](docs/validation.md); known edges and scoped future work
> are in [`docs/limitations-and-guarantees.md`](docs/limitations-and-guarantees.md)).
> No results are fabricated.

## Install

### pip

```bash
pip install "veritas-leakage[cli]"
```

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

## Quickstart

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
