"""Environment-based configuration for sqlastack."""

from __future__ import annotations

from sqlalchemy.engine import make_url
from sqlastack.core.exceptions import ConfigurationError
from sqlastack.core.exceptions import InvalidConnectionString
from sqlastack.core.exceptions import MissingDatabaseURL
import dataclasses
import functools
import logging
import os
import sqlalchemy.exc


logger = logging.getLogger(__name__)


@functools.cache
def _load_dotenv() -> None:
    """Load .env file if python-dotenv is installed. Does not override existing vars.

    Cached: the .env file is parsed at most once per process.
    """
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
    """

    database_url: str
    pool_size: int = 5
    pool_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False
    slow_query_ms: int = 1000

    @classmethod
    def from_env(cls, name: str) -> SQLAStackConfig:
        """Load configuration for the named database from environment variables.

        Reads ``SQLASTACK_<NAME>_URL``, ``SQLASTACK_<NAME>_POOL_SIZE`` etc.
        Attempts to load a .env file first (if python-dotenv is available).

        Raises:
            MissingDatabaseURL: If the URL variable is not set.
            InvalidConnectionString: If the URL is malformed (the message
                never contains credentials).
            ConfigurationError: If a numeric variable is not an integer.
        """
        _load_dotenv()
        upper = name.upper()
        url_key = f"SQLASTACK_{upper}_URL"
        prefix = f"SQLASTACK_{upper}"

        database_url = os.environ.get(url_key, "").strip()
        if not database_url:
            raise MissingDatabaseURL(f"{url_key} environment variable is required")
        try:
            masked = make_url(database_url).render_as_string(hide_password=True)
        except sqlalchemy.exc.ArgumentError as exc:
            raise InvalidConnectionString(
                f"{url_key} is not a valid SQLAlchemy URL"
            ) from exc

        def _int(key: str, default: str) -> int:
            raw = os.environ.get(f"{prefix}_{key}", default)
            try:
                return int(raw)
            except ValueError as exc:
                raise ConfigurationError(
                    f"{prefix}_{key} must be an integer, got: {raw!r}"
                ) from exc

        logger.debug("Loaded config for %r from env (%s)", name, masked)
        return cls(
            database_url=database_url,
            pool_size=_int("POOL_SIZE", "5"),
            pool_overflow=_int("POOL_OVERFLOW", "10"),
            pool_timeout=_int("POOL_TIMEOUT", "30"),
            pool_recycle=_int("POOL_RECYCLE", "3600"),
            pool_pre_ping=_parse_bool(
                os.environ.get(f"{prefix}_POOL_PRE_PING", "true")
            ),
            echo=_parse_bool(os.environ.get(f"{prefix}_ECHO", "false")),
            slow_query_ms=_int("SLOW_QUERY_MS", "1000"),
        )

    @property
    def dialect(self) -> str:
        """Return the dialect name (e.g. 'postgresql')."""
        scheme = self.database_url.split("://")[0]
        return scheme.split("+")[0]

    @property
    def is_postgresql(self) -> bool:
        """Return True if database_url points to PostgreSQL."""
        return self.dialect == "postgresql"
