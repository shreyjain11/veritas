"""Packaging contract: pyproject metadata + version stay consistent and isolated.

These are static checks (no wheel build) -- the clean-checkout CI job
(.github/workflows/ci.yml) actually builds the wheel, installs it, and runs the
suite against it. Here we lock the invariants that make that install correct: the
distribution name, the dynamic-version source, the console entry point, and the
rule that core runtime deps never include the optional / test-only packages.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import veritas

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _pyproject() -> dict[str, Any]:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_distribution_name_is_veritas_audit() -> None:
    assert _pyproject()["project"]["name"] == "veritas-audit"


def test_version_is_released_semver_and_matches_package() -> None:
    proj = _pyproject()
    # The version is dynamic, sourced from the package itself.
    assert "version" in proj["project"]["dynamic"]
    assert proj["tool"]["hatch"]["version"]["path"] == "src/veritas/__init__.py"
    parts = veritas.__version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts), veritas.__version__
    assert veritas.__version__ != "0.0.0"  # an actual release, not the scaffold default


def test_console_entry_point_targets_the_cli_app() -> None:
    assert _pyproject()["project"]["scripts"]["veritas"] == "veritas.cli.app:app"


def test_core_runtime_deps_exclude_optional_and_test_only_packages() -> None:
    deps = " ".join(_pyproject()["project"]["dependencies"]).lower()
    for forbidden in ("typer", "mcp", "scikit-learn", "sklearn"):
        assert forbidden not in deps, f"{forbidden} must not be a core runtime dependency"


def test_optional_extras_are_declared() -> None:
    extras = _pyproject()["project"]["optional-dependencies"]
    assert {"cli", "mcp", "docs"}.issubset(extras)
