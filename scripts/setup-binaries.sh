#!/usr/bin/env bash
#
# Provision the pinned bioinformatics-binary environment (environment.yml) and
# add its bin directory to PATH so the contamination detectors can find
# mmseqs / diamond / foldseek / hmmer.
#
# Usage:
#   source scripts/setup-binaries.sh   # creates the env (if needed) and exports PATH
#   ./scripts/setup-binaries.sh        # creates the env and prints the bin dir
#
# Idempotent: re-running reuses an existing "veritas-bin" environment.
set -euo pipefail

ENV_NAME="veritas-bin"
SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
REPO_ROOT="$(cd "$(dirname "${SCRIPT_SOURCE}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/environment.yml"

# Allow this script to be either sourced or executed; fail cleanly either way.
_fail() {
    echo "error: $*" >&2
    return 1 2>/dev/null || exit 1
}

if command -v micromamba >/dev/null 2>&1; then
    MAMBA=micromamba
elif command -v mamba >/dev/null 2>&1; then
    MAMBA=mamba
elif command -v conda >/dev/null 2>&1; then
    MAMBA=conda
else
    _fail "none of micromamba / mamba / conda found on PATH"
fi

[ -f "${ENV_FILE}" ] || _fail "environment file not found: ${ENV_FILE}"

# Create the environment only if it does not already exist.
if ! "${MAMBA}" env list 2>/dev/null | grep -Eq "(^|[[:space:]/])${ENV_NAME}([[:space:]]|\$)"; then
    echo "creating '${ENV_NAME}' from ${ENV_FILE} ..." >&2
    "${MAMBA}" create -y -f "${ENV_FILE}"
fi

# Resolve the env's bin directory via the location of one of its binaries.
BIN_DIR="$("${MAMBA}" run -n "${ENV_NAME}" sh -c 'dirname "$(command -v mmseqs)"')"
[ -n "${BIN_DIR}" ] || _fail "could not locate binaries in '${ENV_NAME}'"

export PATH="${BIN_DIR}:${PATH}"
echo "${BIN_DIR}"
