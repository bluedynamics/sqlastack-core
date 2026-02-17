"""Engine factory with dialect detection."""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import Engine
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.pool import StaticPool

from sqlastack.core.config import SQLAStackConfig

logger = logging.getLogger(__name__)


def create_sqlastack_engine(config: SQLAStackConfig | None = None) -> Engine:
    """Create a SQLAlchemy Engine with dialect-appropriate settings.

    If config is None, loads from environment via SQLAStackConfig.from_env().

    For PostgreSQL: configures connection pooling with all pool parameters.
    For SQLite in-memory: uses StaticPool with check_same_thread=False.
    For SQLite file: uses default pool settings.
    """
    if config is None:
        config = SQLAStackConfig.from_env()

    kwargs: dict[str, Any] = {"echo": config.echo}

    if config.is_sqlite:
        kwargs.update(_build_sqlite_kwargs(config))
    elif config.is_postgresql:
        kwargs.update(_build_postgresql_kwargs(config))

    engine = create_engine(config.database_url, **kwargs)
    _attach_slow_query_listener(engine, config)
    return engine


def _build_sqlite_kwargs(config: SQLAStackConfig) -> dict[str, Any]:
    """Build engine kwargs for SQLite."""
    if ":memory:" in config.database_url or "mode=memory" in config.database_url:
        return {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        }
    return {}


def _build_postgresql_kwargs(config: SQLAStackConfig) -> dict[str, Any]:
    """Build engine kwargs for PostgreSQL."""
    return {
        "pool_size": config.pool_size,
        "max_overflow": config.pool_overflow,
        "pool_timeout": config.pool_timeout,
        "pool_recycle": config.pool_recycle,
        "pool_pre_ping": config.pool_pre_ping,
    }


def _attach_slow_query_listener(engine: Engine, config: SQLAStackConfig) -> None:
    """Log queries exceeding the slow query threshold."""
    threshold_s = config.slow_query_ms / 1000.0

    @event.listens_for(engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        conn.info["_sqlastack_query_start"] = time.monotonic()

    @event.listens_for(engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        start = conn.info.pop("_sqlastack_query_start", None)
        if start is not None:
            elapsed = time.monotonic() - start
            if elapsed >= threshold_s:
                logger.warning(
                    "Slow query (%.1fms): %s",
                    elapsed * 1000,
                    statement[:200],
                )
