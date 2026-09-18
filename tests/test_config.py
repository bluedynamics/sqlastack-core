"""Tests for the configuration loader (named vocabulary only)."""

from __future__ import annotations

from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.exceptions import ConfigurationError
from sqlastack.core.exceptions import InvalidConnectionString
from sqlastack.core.exceptions import MissingDatabaseURL
import dataclasses
import pytest


def test_from_env_minimal(monkeypatch):
    monkeypatch.setenv("SQLASTACK_FH_URL", "postgresql+psycopg://u:p@h/fh")
    config = SQLAStackConfig.from_env("fh")
    assert config.database_url == "postgresql+psycopg://u:p@h/fh"
    assert config.pool_size == 5
    assert config.pool_pre_ping is True
    assert config.echo is False


def test_from_env_all_vars(monkeypatch):
    monkeypatch.setenv("SQLASTACK_FH_URL", "postgresql://u:p@host:5432/db")
    monkeypatch.setenv("SQLASTACK_FH_POOL_SIZE", "10")
    monkeypatch.setenv("SQLASTACK_FH_POOL_OVERFLOW", "20")
    monkeypatch.setenv("SQLASTACK_FH_POOL_TIMEOUT", "60")
    monkeypatch.setenv("SQLASTACK_FH_POOL_RECYCLE", "1800")
    monkeypatch.setenv("SQLASTACK_FH_POOL_PRE_PING", "false")
    monkeypatch.setenv("SQLASTACK_FH_ECHO", "true")
    monkeypatch.setenv("SQLASTACK_FH_SLOW_QUERY_MS", "500")
    config = SQLAStackConfig.from_env("fh")
    assert config.pool_size == 10
    assert config.pool_overflow == 20
    assert config.pool_timeout == 60
    assert config.pool_recycle == 1800
    assert config.pool_pre_ping is False
    assert config.echo is True
    assert config.slow_query_ms == 500


def test_from_env_missing_url_raises(monkeypatch):
    monkeypatch.delenv("SQLASTACK_FH_URL", raising=False)
    with pytest.raises(MissingDatabaseURL, match="SQLASTACK_FH_URL"):
        SQLAStackConfig.from_env("fh")


def test_from_env_requires_name():
    with pytest.raises(TypeError):
        SQLAStackConfig.from_env()  # type: ignore[call-arg]


def test_legacy_vocabulary_gone(monkeypatch):
    """DATABASE_URL wird nicht mehr gelesen (Review 2026-09-18, Entscheidung)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/legacy")
    monkeypatch.delenv("SQLASTACK_FH_URL", raising=False)
    with pytest.raises(MissingDatabaseURL):
        SQLAStackConfig.from_env("fh")


def test_invalid_url_masks_password(monkeypatch):
    monkeypatch.setenv("SQLASTACK_FH_URL", "not a url with S3cretPW")
    with pytest.raises(InvalidConnectionString) as excinfo:
        SQLAStackConfig.from_env("fh")
    assert "S3cretPW" not in str(excinfo.value)


def test_invalid_port_masks_password(monkeypatch):
    """make_url wirft für einen Nicht-Zahlen-Port einen rohen ValueError —
    auch der muss als InvalidConnectionString ohne Credentials ankommen."""
    monkeypatch.setenv("SQLASTACK_FH_URL", "postgresql://u:S3cretPW@h:badport/db")
    with pytest.raises(InvalidConnectionString) as excinfo:
        SQLAStackConfig.from_env("fh")
    assert "S3cretPW" not in str(excinfo.value)


def test_invalid_int_raises_configuration_error(monkeypatch):
    monkeypatch.setenv("SQLASTACK_FH_URL", "postgresql://u:p@h/db")
    monkeypatch.setenv("SQLASTACK_FH_POOL_SIZE", "abc")
    with pytest.raises(ConfigurationError, match="SQLASTACK_FH_POOL_SIZE"):
        SQLAStackConfig.from_env("fh")


def test_invalid_bool_raises_configuration_error(monkeypatch):
    monkeypatch.setenv("SQLASTACK_FH_URL", "postgresql://u:p@h/db")
    monkeypatch.setenv("SQLASTACK_FH_ECHO", "ture")
    with pytest.raises(ConfigurationError, match="SQLASTACK_FH_ECHO"):
        SQLAStackConfig.from_env("fh")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
    ],
)
def test_boolean_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("SQLASTACK_FH_URL", "postgresql://u:p@h/db")
    monkeypatch.setenv("SQLASTACK_FH_ECHO", value)
    config = SQLAStackConfig.from_env("fh")
    assert config.echo is expected


def test_schema_field_removed():
    assert "schema" not in {f.name for f in dataclasses.fields(SQLAStackConfig)}


def test_dialect_and_is_postgresql():
    config = SQLAStackConfig(database_url="postgresql+psycopg2://u:p@host/db")
    assert config.dialect == "postgresql"
    assert config.is_postgresql is True


def test_config_is_immutable():
    config = SQLAStackConfig(database_url="postgresql://u:p@h/db")
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.pool_size = 99
