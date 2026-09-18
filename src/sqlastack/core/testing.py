"""Shared PostgreSQL pytest fixtures for sqlastack and downstream packages.

Usage in a downstream top-level ``conftest.py``::

    pytest_plugins = ["sqlastack.core.testing"]

Requires the ``test`` extra (pytest, testcontainers, psycopg).
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def pg_url():
    """Connection URL of a session-scoped PostgreSQL testcontainer."""
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16") as pg:
        yield pg.get_connection_url(driver="psycopg")


@pytest.fixture(scope="session")
def pg_config(pg_url):
    from sqlastack.core.config import SQLAStackConfig

    return SQLAStackConfig(database_url=pg_url)


@pytest.fixture(scope="session")
def pg_engine(pg_config):
    """Engine with all SQLModel metadata created (schemas included)."""
    from sqlalchemy import text
    from sqlastack.core.engine import create_sqlastack_engine
    from sqlmodel import SQLModel

    engine = create_sqlastack_engine(pg_config)
    schemas = {
        table.schema
        for table in SQLModel.metadata.tables.values()
        if table.schema is not None
    }
    with engine.begin() as conn:
        for schema in sorted(schemas):
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def pg_registry(pg_engine):
    """DatabaseRegistry with the shared test engine registered as ``fh``.

    Reuses the warm session-scoped engine (no per-test connect cost). The
    engine belongs to the ``pg_engine`` fixture — teardown only removes this
    thread's zope sessions, it does NOT dispose.
    """
    from sqlastack.core.registry import DatabaseRegistry
    from sqlastack.core.session import SessionFactory

    registry = DatabaseRegistry()
    registry.register_factory("fh", SessionFactory(engine=pg_engine))
    yield registry
    registry.remove_zope_sessions()


@pytest.fixture(autouse=True)
def _truncate_pg(request):
    """Truncate all SQLModel tables after each test that used pg_engine."""
    yield
    if "pg_engine" not in request.fixturenames:
        return
    from sqlalchemy import text
    from sqlmodel import SQLModel

    engine = request.getfixturevalue("pg_engine")
    preparer = engine.dialect.identifier_preparer
    names = [
        preparer.format_table(table)
        for table in reversed(SQLModel.metadata.sorted_tables)
    ]
    if not names:
        return
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(names)} RESTART IDENTITY CASCADE"))
