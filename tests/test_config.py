"""Tests for the configuration loader."""

from __future__ import annotations

import dataclasses

import pytest

from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.exceptions import InvalidConnectionString
from sqlastack.core.exceptions import MissingDatabaseURL


def test_from_env_minimal(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    config = SQLAStackConfig.from_env()
    assert config.database_url == "sqlite:///:memory:"
    assert config.pool_size == 5
    assert config.pool_pre_ping is True
    assert config.echo is False


def test_from_env_all_vars(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host:5432/db")
    monkeypatch.setenv("SQL_POOL_SIZE", "10")
    monkeypatch.setenv("SQL_POOL_OVERFLOW", "20")
    monkeypatch.setenv("SQL_POOL_TIMEOUT", "60")
    monkeypatch.setenv("SQL_POOL_RECYCLE", "1800")
    monkeypatch.setenv("SQL_POOL_PRE_PING", "false")
    monkeypatch.setenv("SQL_ECHO", "true")
    monkeypatch.setenv("SQL_SLOW_QUERY_MS", "500")
    monkeypatch.setenv("SQL_SCHEMA", "myschema")
    config = SQLAStackConfig.from_env()
    assert config.pool_size == 10
    assert config.pool_overflow == 20
    assert config.pool_timeout == 60
    assert config.pool_recycle == 1800
    assert config.pool_pre_ping is False
    assert config.echo is True
    assert config.slow_query_ms == 500
    assert config.schema == "myschema"


def test_from_env_missing_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(MissingDatabaseURL):
        SQLAStackConfig.from_env()


def test_from_env_invalid_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "not-a-url")
    with pytest.raises(InvalidConnectionString):
        SQLAStackConfig.from_env()


@pytest.mark.parametrize(
    ("value", "expected"),
    [("true", True), ("True", True), ("1", True), ("yes", True),
     ("false", False), ("False", False), ("0", False), ("no", False)],
)
def test_boolean_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("SQL_ECHO", value)
    config = SQLAStackConfig.from_env()
    assert config.echo is expected


def test_is_sqlite():
    config = SQLAStackConfig(database_url="sqlite:///:memory:")
    assert config.is_sqlite is True
    assert config.is_postgresql is False


def test_is_postgresql():
    config = SQLAStackConfig(database_url="postgresql://u:p@host/db")
    assert config.is_postgresql is True
    assert config.is_sqlite is False


def test_dialect_postgresql_psycopg2():
    config = SQLAStackConfig(database_url="postgresql+psycopg2://u:p@host/db")
    assert config.dialect == "postgresql"
    assert config.is_postgresql is True


def test_dialect_sqlite():
    config = SQLAStackConfig(database_url="sqlite:///test.db")
    assert config.dialect == "sqlite"


def test_config_is_immutable():
    config = SQLAStackConfig(database_url="sqlite:///:memory:")
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.pool_size = 99
