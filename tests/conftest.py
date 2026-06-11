"""Shared test fixtures for sqlastack-core."""

from __future__ import annotations

from sqlalchemy import Engine
from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.engine import create_sqlastack_engine
from sqlastack.core.session import SessionFactory
from sqlastack.core.testing import register_pg_fixtures
from sqlmodel import SQLModel
import pytest


register_pg_fixtures(globals())


@pytest.fixture
def sqlite_config() -> SQLAStackConfig:
    """Provide an in-memory SQLite config."""
    return SQLAStackConfig(database_url="sqlite:///:memory:")


@pytest.fixture
def engine(sqlite_config: SQLAStackConfig) -> Engine:
    """Provide a SQLite in-memory engine with all tables created."""
    eng = create_sqlastack_engine(sqlite_config)
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> SessionFactory:
    """Provide a SessionFactory backed by SQLite in-memory."""
    return SessionFactory(engine=engine)
