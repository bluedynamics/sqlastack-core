"""Tests for the engine factory (PostgreSQL)."""

from __future__ import annotations

from sqlalchemy import text
from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.engine import create_sqlastack_engine
import dataclasses


def test_create_engine_applies_pool_settings(pg_config):
    config = dataclasses.replace(pg_config, pool_size=7, pool_overflow=3)
    engine = create_sqlastack_engine(config)
    assert engine.pool.size() == 7
    assert engine.pool._max_overflow == 3
    engine.dispose()


def test_create_engine_echo(pg_config):
    config = dataclasses.replace(pg_config, echo=True)
    engine = create_sqlastack_engine(config)
    assert engine.echo is True
    engine.dispose()


def test_engine_connects(pg_engine):
    with pg_engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1


def test_sqlite_special_path_removed():
    """Spec §13: kein SQLite-Sonderpfad mehr."""
    import sqlastack.core.engine as engine_mod

    assert not hasattr(engine_mod, "_build_sqlite_kwargs")
    assert not hasattr(SQLAStackConfig, "is_sqlite")
