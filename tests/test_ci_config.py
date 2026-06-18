"""CI configuration contract (text-level).

PyYAML is not a project dependency, so these assert against the raw workflow
text. They lock the guarantees the build promises: the deterministic-Hypothesis
profile is live on the core test job, the clean-checkout job builds and installs
a wheel and re-checks no-extras isolation, the coverage gate is wired, and the
determinism gate runs only on the single pinned platform.
"""

from __future__ import annotations

from pathlib import Path

CI = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml").read_text(
    encoding="utf-8"
)


def test_hypothesis_ci_profile_is_live() -> None:
    assert "HYPOTHESIS_PROFILE: ci" in CI


def test_coverage_gate_is_wired() -> None:
    assert "--cov-fail-under=90" in CI


def test_unix_sockets_allowed_wherever_network_is_blocked() -> None:
    # The hermetic policy blocks NETWORK (AF_INET), but asyncio's event-loop
    # self-pipe and the MCP in-memory transport use local AF_UNIX socketpairs.
    # Every --disable-socket must be paired with --allow-unix-socket, matching the
    # conftest's disable_socket(allow_unix_socket=True). Regression guard: a bare
    # --disable-socket broke test-core on the first CI run (run 27777630398).
    assert "--allow-unix-socket" in CI
    assert CI.count("--disable-socket") == CI.count("--allow-unix-socket")


def test_clean_checkout_job_builds_installs_and_isolates() -> None:
    assert "clean-checkout" in CI
    assert "uv build --wheel" in CI
    assert "dist/*.whl" in CI
    # the no-extras isolation assertion must be present in the job
    assert "leaked into a core-only install" in CI


def test_determinism_gate_runs_on_the_pinned_platform() -> None:
    assert "determinism gate (py3.12)" in CI


def test_docs_validation_is_enforced_in_ci() -> None:
    # mkdocs build --strict + the limitations-page-matches-constants honesty test
    # must run in CI, not just locally: a dedicated docs job installs the docs
    # extra (so the strict build runs instead of skipping) and runs tests/docs.
    assert "--extra docs" in CI
    assert "tests/docs" in CI
