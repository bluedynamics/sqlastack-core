"""Exception hierarchy for sqlastack."""

from __future__ import annotations

import sqlalchemy.exc


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
    """Raised when the ``SQLASTACK_<NAME>_URL`` variable is not set."""


class InvalidConnectionString(ConfigurationError):
    """Raised when the connection string is malformed."""


class ZopeNotAvailable(ConfigurationError):
    """Raised when a Zope session is requested but zope.sqlalchemy is not installed."""


class UnknownDatabase(ConfigurationError):
    """Raised when a database name is requested that is not registered."""


# --- Transaction ---


class TransactionError(SQLAStackError):
    """Base for transaction-related errors."""


class CommitFailed(TransactionError):
    """Raised when commit fails."""


class RollbackFailed(TransactionError):
    """Raised when rollback fails."""


# --- Query ---


class QueryError(SQLAStackError):
    """Base for query-related errors."""


class IntegrityError(QueryError):
    """Raised when a constraint is violated."""


class DataError(QueryError):
    """Raised when data is invalid for the column type."""


class ProgrammingError(QueryError):
    """Raised for SQL syntax errors or invalid operations."""


def translate_exception(exc: sqlalchemy.exc.SQLAlchemyError) -> SQLAStackError:
    """Translate a SQLAlchemy exception into the matching sqlastack exception.

    Returns the translated exception instance (does not raise). Used at the
    flush boundary (Repository) and at the commit boundary (session_scope) so
    both session modes surface the SAME sqlastack exception types.
    """
    if isinstance(exc, sqlalchemy.exc.IntegrityError):
        return IntegrityError(str(exc), original=exc)
    if isinstance(exc, sqlalchemy.exc.DataError):
        return DataError(str(exc), original=exc)
    if isinstance(exc, sqlalchemy.exc.ProgrammingError):
        return ProgrammingError(str(exc), original=exc)
    return CommitFailed(str(exc), original=exc)
