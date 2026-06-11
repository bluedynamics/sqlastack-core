"""Exception hierarchy for sqlastack."""

from __future__ import annotations


class SQLAStackError(Exception):
    """Base exception for all sqlastack errors."""

    def __init__(self, message: str, original: Exception | None = None) -> None:
        self.original = original
        if original is not None:
            message = f"{message} (caused by {type(original).__name__}: {original})"
        super().__init__(message)


# --- Configuration ---


class ConfigurationError(SQLAStackError):
    """Raised for configuration problems."""


class MissingDatabaseURL(ConfigurationError):
    """Raised when DATABASE_URL is not set."""


class InvalidConnectionString(ConfigurationError):
    """Raised when the connection string is malformed."""


class ZopeNotAvailable(ConfigurationError):
    """Raised when zope=True is requested but zope.sqlalchemy is not installed."""


class UnknownDatabase(ConfigurationError):
    """Raised when a database name is requested that is not registered."""


# --- Connection ---


class ConnectionError(SQLAStackError):
    """Base for connection-related errors."""


class ConnectionTimeout(ConnectionError):
    """Raised when connection attempt times out."""


class ConnectionRefused(ConnectionError):
    """Raised when database refuses connection."""


class PoolExhausted(ConnectionError):
    """Raised when connection pool has no available connections."""


# --- Transaction ---


class TransactionError(SQLAStackError):
    """Base for transaction-related errors."""


class CommitFailed(TransactionError):
    """Raised when commit fails."""


class RollbackFailed(TransactionError):
    """Raised when rollback fails."""


class TwoPhaseCommitFailed(TransactionError):
    """Raised when two-phase commit fails."""


# --- Query ---


class QueryError(SQLAStackError):
    """Base for query-related errors."""


class IntegrityError(QueryError):
    """Raised when a constraint is violated."""


class DataError(QueryError):
    """Raised when data is invalid for the column type."""


class ProgrammingError(QueryError):
    """Raised for SQL syntax errors or invalid operations."""


# --- Migration ---


class MigrationError(SQLAStackError):
    """Base for migration-related errors."""


class MigrationFailed(MigrationError):
    """Raised when a migration execution fails."""


class MigrationConflict(MigrationError):
    """Raised when migration versions conflict."""
