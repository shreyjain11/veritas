# syntax=docker/dockerfile:1
#
# Veritas — portable, batteries-included auditor image.
#
# Bakes in the version-pinned contamination-detector binaries (mmseqs2, diamond,
# foldseek, hmmer) at the SAME pins as environment.yml / the provenance contract,
# plus Python 3.12 and the `veritas` CLI. The result: `docker run veritas-audit
# audit ...` runs the full pipeline on any machine with Docker, regardless of OS,
# with no conda/bioconda setup on the host.
#
# Pinned to linux/amd64: that is what bioconda publishes these exact builds for,
# and the platform the determinism gate is pinned to (so the baked binaries match
# the provenance versions byte-for-byte). On Apple Silicon it runs under emulation.
#
#   docker build -t veritas-audit .
#   docker run --rm veritas-audit --help
#   docker run --rm -v "$PWD:/work" veritas-audit audit --sequences ... --out /work/report.json

FROM --platform=linux/amd64 mambaorg/micromamba:1.5.10

LABEL org.opencontainers.image.title="veritas-audit" \
      org.opencontainers.image.source="https://github.com/shreyjain11/veritas" \
      org.opencontainers.image.description="Post-hoc leakage & robustness auditor with pinned detector binaries baked in."

# 1) Pinned detector binaries + Python 3.12 into the base conda env. The pins live
#    in environment.yml (mmseqs2=18.8cc5c, diamond=2.2.1, foldseek=10.941cd33,
#    hmmer=3.4) — the single source of truth shared with CI and the provenance record.
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml python=3.12 pip \
    && micromamba clean --all --yes

# Activate the base env for the RUN steps below and for the entrypoint.
ARG MAMBA_DOCKERFILE_ACTIVATE=1

# 2) Install veritas + the CLI extra from source (hatchling builds the wheel in-image).
WORKDIR /app
COPY --chown=$MAMBA_USER:$MAMBA_USER pyproject.toml README.md LICENSE CHANGELOG.md ./
COPY --chown=$MAMBA_USER:$MAMBA_USER src ./src
# `polars[rtcompat]` selects the runtime-compatible build that runs on baseline
# x86-64 without AVX2/FMA — so the image works on older amd64 hosts and under
# emulation, not only on modern CPUs. polars is used only for light table IO here,
# so the non-vectorized runtime has negligible cost.
RUN pip install --no-cache-dir ".[cli]" "polars[rtcompat]"

# 3) Bake in the tiny runnable quickstart so the image self-tests with no mount.
COPY --chown=$MAMBA_USER:$MAMBA_USER examples /opt/veritas/examples

# 4) Build-time smoke test: the CLI runs and every pinned detector is installed on
#    PATH. We verify presence, not execution — actually running the detectors
#    exercises the host CPU's instruction set (the bioconda builds use AVX2), which
#    is a runtime concern and would spuriously fail when the image is BUILT under
#    emulation on a non-amd64 host. Execution is covered by the docker.yml CI job,
#    which builds and runs a full audit on native amd64 runners.
RUN veritas --help >/dev/null \
    && for b in mmseqs diamond foldseek hmmsearch; do \
         command -v "$b" >/dev/null || { echo "MISSING DETECTOR: $b" >&2; exit 1; }; \
       done \
    && echo "image OK: veritas CLI + mmseqs2/diamond/foldseek/hmmer present"

# Audits run on data mounted into /work; reports are written back there.
WORKDIR /work
ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "veritas"]
CMD ["--help"]
