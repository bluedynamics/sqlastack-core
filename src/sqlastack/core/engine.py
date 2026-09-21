"""Engine factory with dialect detection."""

from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlastack.core.config import SQLAStackConfig
from typing import Any
import logging
import time


logger = logging.getLogger(__name__)


def create_sqlastack_engine(config: SQLAStackConfig) -> Engine:
    """Create a SQLAlchemy Engine with dialect-appropriate settings.

    For PostgreSQL: configures connection pooling with all pool parameters.
    Other dialects get SQLAlchemy's defaults.
    """
    kwargs: dict[str, Any] = {"echo": config.echo}

    if config.is_postgresql:
        kwargs.update(_build_postgresql_kwargs(config))

    engine = create_engine(config.database_url, **kwargs)
    _attach_slow_query_listener(engine, config)
    return engine


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
