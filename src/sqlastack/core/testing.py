"""Test utilities for sqlastack and downstream packages."""

from __future__ import annotations

from sqlalchemy import Engine

from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.engine import create_sqlastack_engine
from sqlastack.core.session import SessionFactory


def sqlite_memory_config() -> SQLAStackConfig:
    """Return a config for SQLite in-memory database."""
    return SQLAStackConfig(database_url="sqlite:///:memory:")


def sqlite_memory_engine() -> Engine:
    """Return an engine for SQLite in-memory database."""
    return create_sqlastack_engine(sqlite_memory_config())


def create_test_session_factory() -> SessionFactory:
    """Return a SessionFactory configured for SQLite in-memory."""
    return SessionFactory(config=sqlite_memory_config())


def register_pg_fixtures(namespace: dict) -> None:
    """Inject the shared PostgreSQL pytest fixtures into a conftest namespace.

    Usage in a downstream conftest.py:

        from sqlastack.core.testing import register_pg_fixtures
        register_pg_fixtures(globals())
    """
    from sqlalchemy import text
    from sqlastack.core.config import SQLAStackConfig
    from sqlastack.core.engine import create_sqlastack_engine
    from sqlmodel import SQLModel
    import pytest

    @pytest.fixture(scope="session")
    def pg_url():
        from testcontainers.postgres import PostgresContainer

        with PostgresContainer("postgres:16") as pg:
            yield pg.get_connection_url(driver="psycopg")

    @pytest.fixture(scope="session")
    def pg_config(pg_url):
        return SQLAStackConfig(database_url=pg_url)

    @pytest.fixture(scope="session")
    def pg_engine(pg_config):
        eng = create_sqlastack_engine(pg_config)
        SQLModel.metadata.create_all(eng)
        yield eng
        eng.dispose()

    @pytest.fixture(autouse=True)
    def _truncate_pg(request):
        yield
        if "pg_engine" not in request.fixturenames:
            return
        engine = request.getfixturevalue("pg_engine")
        names = [t.name for t in reversed(SQLModel.metadata.sorted_tables)]
        if not names:
            return
        joined = ", ".join(f'"{n}"' for n in names)
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE {joined} RESTART IDENTITY CASCADE"))

    namespace["pg_url"] = pg_url
    namespace["pg_config"] = pg_config
    namespace["pg_engine"] = pg_engine
    namespace["_truncate_pg"] = _truncate_pg
