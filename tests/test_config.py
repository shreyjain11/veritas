"""Tests for cache-directory resolution (docs/PLAN.md decision #17)."""

from __future__ import annotations

from pathlib import Path

import pytest

from veritas import config


def test_cache_dir_uses_explicit_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.CACHE_DIR_ENV, "/tmp/custom-veritas")
    assert config.cache_dir() == Path("/tmp/custom-veritas")


def test_cache_dir_uses_xdg_when_no_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.CACHE_DIR_ENV, raising=False)
    monkeypatch.setenv(config.XDG_CACHE_HOME_ENV, "/tmp/xdg")
    assert config.cache_dir() == Path("/tmp/xdg/veritas")


def test_cache_dir_falls_back_to_home_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.CACHE_DIR_ENV, raising=False)
    monkeypatch.delenv(config.XDG_CACHE_HOME_ENV, raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/home/tester")))
    assert config.cache_dir() == Path("/home/tester/.cache/veritas")
