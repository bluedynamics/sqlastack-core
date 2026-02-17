"""Tests for the exception hierarchy."""

from __future__ import annotations

import inspect

import sqlastack.core.exceptions as exc_mod
from sqlastack.core.exceptions import CommitFailed
from sqlastack.core.exceptions import ConfigurationError
from sqlastack.core.exceptions import ConnectionError
from sqlastack.core.exceptions import ConnectionRefused
from sqlastack.core.exceptions import ConnectionTimeout
from sqlastack.core.exceptions import DataError
from sqlastack.core.exceptions import IntegrityError
from sqlastack.core.exceptions import InvalidConnectionString
from sqlastack.core.exceptions import MigrationConflict
from sqlastack.core.exceptions import MigrationError
from sqlastack.core.exceptions import MigrationFailed
from sqlastack.core.exceptions import MissingDatabaseURL
from sqlastack.core.exceptions import PoolExhausted
from sqlastack.core.exceptions import ProgrammingError
from sqlastack.core.exceptions import QueryError
from sqlastack.core.exceptions import RollbackFailed
from sqlastack.core.exceptions import SQLAStackError
from sqlastack.core.exceptions import TransactionError
from sqlastack.core.exceptions import TwoPhaseCommitFailed


def test_base_error_message():
    err = SQLAStackError("something broke")
    assert str(err) == "something broke"
    assert err.original is None


def test_base_error_with_original():
    original = ValueError("bad value")
    err = SQLAStackError("wrapper", original=original)
    assert err.original is original
    assert "bad value" in str(err)
    assert "ValueError" in str(err)


def test_hierarchy_configuration():
    assert issubclass(ConfigurationError, SQLAStackError)
    assert issubclass(MissingDatabaseURL, ConfigurationError)
    assert issubclass(InvalidConnectionString, ConfigurationError)


def test_hierarchy_connection():
    assert issubclass(ConnectionError, SQLAStackError)
    assert issubclass(ConnectionTimeout, ConnectionError)
    assert issubclass(ConnectionRefused, ConnectionError)
    assert issubclass(PoolExhausted, ConnectionError)


def test_hierarchy_transaction():
    assert issubclass(TransactionError, SQLAStackError)
    assert issubclass(CommitFailed, TransactionError)
    assert issubclass(RollbackFailed, TransactionError)
    assert issubclass(TwoPhaseCommitFailed, TransactionError)


def test_hierarchy_query():
    assert issubclass(QueryError, SQLAStackError)
    assert issubclass(IntegrityError, QueryError)
    assert issubclass(DataError, QueryError)
    assert issubclass(ProgrammingError, QueryError)


def test_hierarchy_migration():
    assert issubclass(MigrationError, SQLAStackError)
    assert issubclass(MigrationFailed, MigrationError)
    assert issubclass(MigrationConflict, MigrationError)


def test_all_exceptions_are_sqlastack_error():
    """Every exception class in the module must be a subclass of SQLAStackError."""
    for name, obj in inspect.getmembers(exc_mod, inspect.isclass):
        if issubclass(obj, Exception) and obj is not SQLAStackError:
            assert issubclass(obj, SQLAStackError), f"{name} is not a SQLAStackError"
