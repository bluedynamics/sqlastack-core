"""Tests for named (multi-DB) configuration loading."""

from __future__ import annotations

import pytest

from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.exceptions import MissingDatabaseURL


def test_from_env_named_reads_prefixed_url(monkeypatch):
    monkeypatch.setenv("SQLASTACK_FH_URL", "postgresql+psycopg://u:p@h/fh")
    monkeypatch.setenv("SQLASTACK_FH_POOL_SIZE", "7")

    config = SQLAStackConfig.from_env(name="fh")

    assert config.database_url == "postgresql+psycopg://u:p@h/fh"
    assert config.pool_size == 7


def test_from_env_named_missing_url_raises(monkeypatch):
    monkeypatch.delenv("SQLASTACK_FH_URL", raising=False)
    with pytest.raises(MissingDatabaseURL, match="SQLASTACK_FH_URL"):
        SQLAStackConfig.from_env(name="fh")


def test_from_env_legacy_unnamed_still_works(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h/legacy")
    config = SQLAStackConfig.from_env()
    assert config.database_url == "postgresql+psycopg://u:p@h/legacy"
