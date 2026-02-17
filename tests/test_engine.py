"""Tests for the engine factory."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.pool import StaticPool

from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.engine import create_sqlastack_engine


def test_create_engine_sqlite_memory():
    config = SQLAStackConfig(database_url="sqlite:///:memory:")
    engine = create_sqlastack_engine(config)
    assert engine is not None
    assert isinstance(engine.pool, StaticPool)
    engine.dispose()


def test_create_engine_sqlite_file(tmp_path):
    db_path = tmp_path / "test.db"
    config = SQLAStackConfig(database_url=f"sqlite:///{db_path}")
    engine = create_sqlastack_engine(config)
    assert engine is not None
    assert not isinstance(engine.pool, StaticPool)
    engine.dispose()


def test_create_engine_echo():
    config = SQLAStackConfig(database_url="sqlite:///:memory:", echo=True)
    engine = create_sqlastack_engine(config)
    assert engine.echo is True
    engine.dispose()


def test_engine_connects():
    config = SQLAStackConfig(database_url="sqlite:///:memory:")
    engine = create_sqlastack_engine(config)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    engine.dispose()


def test_create_engine_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_sqlastack_engine()
    assert engine is not None
    engine.dispose()
