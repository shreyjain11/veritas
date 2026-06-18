"""(b) The CLI surface and its hermeticity.

`veritas` is a typer app exposing audit / leakage / rescore / stratify. These tests
stay hermetic by: (1) running in-process via typer's CliRunner (no subprocess, no
real `veritas` binary); (2) exercising only help, argument validation, and clean
failure on missing inputs -- never triggering detection (so no mmseqs/foldseek/etc.);
(3) sockets are disabled by the conftest. typer is an optional `cli` extra, so the
module is skipped when it is not installed (core CI is typer-free).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("typer")

from typer.testing import CliRunner

from veritas.cli import app

runner = CliRunner()

_SUBCOMMANDS = ("audit", "leakage", "rescore", "stratify", "gate")


def test_help_lists_all_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in _SUBCOMMANDS:
        assert command in result.output


def test_each_subcommand_has_help() -> None:
    for command in _SUBCOMMANDS:
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0


def test_audit_without_required_options_is_a_usage_error() -> None:
    result = runner.invoke(app, ["audit"])
    assert result.exit_code == 2  # click/typer usage error, not a crash


def test_audit_on_missing_inputs_fails_cleanly(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "audit",
            "--sequences",
            str(tmp_path / "eval.fasta"),
            "--table",
            str(tmp_path / "table.csv"),
            "--reference",
            str(tmp_path / "reference.fasta"),
            "--config",
            str(tmp_path / "config.json"),
            "--out",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code != 0  # clean nonzero exit, no detection invoked
