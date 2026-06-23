# Veritas

A **model-agnostic, post-hoc leakage & robustness auditor** for sequence-based
biological predictors. Point it at a benchmark (sequences + labels + a declared
split, or a model + its reference set) and a model's per-example predictions, and
it produces a rigorous, fully provenance-stamped audit: cross-set contamination
detection, the reported-vs-honest metric on the de-leaked set, and a stratified
"silent failure" analysis.

> **Status:** The audit engine, its interfaces, **and the validation suite** are
> **complete** (100% test coverage; `ruff`, `ruff format`, and `mypy --strict` all
> gate). Four demonstrations/reproductions — OverfitNN homology inflation (R3),
> genomic reverse-complement detection (R2), ProteinGym MSA-depth stratification,
> and PPI family + structural leakage detection — report **real, locked numbers on
> pinned data** (see [`docs/validation.md`](docs/validation.md); known edges and
> scoped future work are in
> [`docs/limitations-and-guarantees.md`](docs/limitations-and-guarantees.md)). No
> results are fabricated.

## Install

```bash
pip install "veritas-audit[cli]"
```

The core package is dependency-light and importable without the optional layers;
the `cli` extra adds the `veritas` command, `mcp` exposes an MCP server, and
`docs` builds the documentation site. Detection backends (`mmseqs2`, `hmmer`,
`foldseek`) are external binaries — see below. Full usage is in the
[documentation](https://shreyjain11.github.io/veritas/) (`docs/` in-repo).

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

The exact pins live in `environment.yml`.

## Rule precedence

This repository carries both the project constitution (`CLAUDE.md` + `docs/SPEC.md`)
and a set of generic ECC harness rule files under `.claude/rules/ecc/`. **Where
they conflict, `CLAUDE.md` and `docs/SPEC.md` are authoritative.** For example,
the test-coverage gate is **90%** (CLAUDE.md), which overrides the 80% stated in
the generic `testing.md` rule file.

## License

MIT — see `LICENSE`.
