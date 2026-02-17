"""Environment-based configuration for sqlastack."""

from __future__ import annotations

import dataclasses
import os

from sqlastack.core.exceptions import InvalidConnectionString
from sqlastack.core.exceptions import MissingDatabaseURL


def _load_dotenv() -> None:
    """Load .env file if python-dotenv is installed. Does not override existing vars."""
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    except ImportError:
        pass


def _parse_bool(value: str) -> bool:
    """Parse a boolean from a string."""
    return value.strip().lower() in ("true", "1", "yes")


@dataclasses.dataclass(frozen=True)
class SQLAStackConfig:
    """Immutable configuration loaded from environment variables.

    Attributes:
        database_url: SQLAlchemy connection URL (required).
        pool_size: Base pool size (PostgreSQL only). Default 5.
        pool_overflow: Max overflow connections. Default 10.
        pool_timeout: Seconds to wait for connection. Default 30.
        pool_recycle: Seconds before connection recycling. Default 3600.
        pool_pre_ping: Health check before query. Default True.
        echo: Log SQL statements. Default False.
        slow_query_ms: Slow query threshold in milliseconds. Default 1000.
        schema: PostgreSQL schema name. Default "public".
    """

    database_url: str
    pool_size: int = 5
    pool_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False
    slow_query_ms: int = 1000
    schema: str = "public"

    @classmethod
    def from_env(cls) -> SQLAStackConfig:
        """Load configuration from environment variables.

        Attempts to load .env file first (if python-dotenv available).

        Raises:
            MissingDatabaseURL: If DATABASE_URL is not set.
            InvalidConnectionString: If DATABASE_URL is malformed.
        """
        _load_dotenv()

        database_url = os.environ.get("DATABASE_URL", "").strip()
        if not database_url:
            raise MissingDatabaseURL("DATABASE_URL environment variable is required")
        if "://" not in database_url:
            raise InvalidConnectionString(
                f"DATABASE_URL must contain '://' scheme separator, got: {database_url!r}"
            )

        return cls(
            database_url=database_url,
            pool_size=int(os.environ.get("SQL_POOL_SIZE", "5")),
            pool_overflow=int(os.environ.get("SQL_POOL_OVERFLOW", "10")),
            pool_timeout=int(os.environ.get("SQL_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.environ.get("SQL_POOL_RECYCLE", "3600")),
            pool_pre_ping=_parse_bool(os.environ.get("SQL_POOL_PRE_PING", "true")),
            echo=_parse_bool(os.environ.get("SQL_ECHO", "false")),
            slow_query_ms=int(os.environ.get("SQL_SLOW_QUERY_MS", "1000")),
            schema=os.environ.get("SQL_SCHEMA", "public"),
        )

    @property
    def dialect(self) -> str:
        """Return the dialect name (e.g. 'sqlite', 'postgresql')."""
        scheme = self.database_url.split("://")[0]
        return scheme.split("+")[0]

    @property
    def is_sqlite(self) -> bool:
        """Return True if database_url points to SQLite."""
        return self.dialect == "sqlite"

    @property
    def is_postgresql(self) -> bool:
        """Return True if database_url points to PostgreSQL."""
        return self.dialect == "postgresql"
