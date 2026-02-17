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
