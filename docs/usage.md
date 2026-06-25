# Usage

Two supported install paths. Use **Docker** to have the detector binaries handled
for you on any OS; use **pip** if you already manage MMseqs2 / HMMER / Foldseek.

## Install — Docker (binaries baked in, any OS)

The image bakes in the version-pinned detectors (mmseqs2, diamond, foldseek,
hmmer — see `environment.yml`) plus the CLI, so it runs anywhere Docker does with
no conda/bioconda setup on the host:

```bash
docker build -t veritas-audit .
docker run --rm veritas-audit --help

# audit your own data: mount the directory, write the report back into it
docker run --rm -v "$PWD:/work" veritas-audit audit \
  --sequences /work/eval.fasta --table /work/table.csv \
  --reference /work/reference.fasta --config /work/config.json \
  --metric accuracy --out /work/report.json
```

The baked binaries are pinned to the same versions recorded in the report's
provenance, so results reproduce across machines. The image is built for
`linux/amd64` (it runs under emulation on Apple Silicon). A ready-to-run
quickstart is bundled at `/opt/veritas/examples/quickstart` inside the image.

## Install — pip (you provide the binaries)

```bash
pip install "veritas-audit[cli]"
```

The core package is dependency-light. The `cli` extra adds the `veritas`
command; the `mcp` extra exposes the auditor as an MCP server; the `docs` extra
builds this site. Plain `pip install veritas-audit` installs the library only.

Detection backends (MMseqs2, HMMER, Foldseek) are external binaries. Install the
pinned versions with `micromamba create -f environment.yml` (then
`source scripts/setup-binaries.sh`), or install your own and point Veritas at a
specific binary with `VERITAS_MMSEQS_BIN` / `VERITAS_HMMER_BIN` /
`VERITAS_FOLDSEEK_BIN`. The resolved absolute path and version are recorded in the
report's provenance.

## Inputs

| Input | What it is |
| --- | --- |
| `--sequences` | Evaluation sequences (FASTA). |
| `--table` | CSV with `id,label,prediction` per evaluation item. |
| `--reference` | The set the model could have memorized (FASTA). |
| `--config` | An [`AuditConfig`](api.md) as JSON (detectors, seed, policies). |

## Run an audit

```bash
veritas audit \
  --sequences eval.fasta \
  --table table.csv \
  --reference reference.fasta \
  --config config.json \
  --metric auroc \
  --out report.json
```

The report contains the reported metric, the honest (de-leaked) metric, the
leakage summary, per-axis stratification, disclosed limitations, and the
`audit_hash`. Render Markdown or HTML by changing the `--out` extension (or
`--format`).

## Gate a CI pipeline

`veritas gate` fails the build when the reported-vs-honest gap exceeds a
threshold — and **fails loudly** when the honest metric is undefined or there is
insufficient clean data (it never silently passes):

```bash
veritas gate --report report.json --max-delta 0.05
```

## Subcommands

- `veritas audit` — full pipeline (detect → de-leak → re-score → stratify → report).
- `veritas leakage` — detection only; writes the contamination graph.
- `veritas rescore` — honest re-scoring from a precomputed graph.
- `veritas stratify` — stratified metrics from a precomputed graph.
- `veritas gate` — pass/fail a report against a max leakage delta.

See the [GitHub Action](#github-action) for a drop-in CI integration.

## GitHub Action

A composite action wraps audit + gate for CI. A minimal workflow:

```yaml
- uses: shreyjain11/veritas@v0.1.0
  with:
    sequences: eval.fasta
    table: table.csv
    reference: reference.fasta
    config: config.json
    metric: auroc
    max-delta: "0.05"
```

The action installs its own pinned package and sets up the detection binaries.
A runnable end-to-end example lives in `examples/quickstart/`.
