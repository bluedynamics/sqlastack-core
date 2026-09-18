"""Tests for the exception hierarchy."""

from __future__ import annotations

from sqlastack.core.exceptions import CommitFailed
from sqlastack.core.exceptions import ConfigurationError
from sqlastack.core.exceptions import DataError
from sqlastack.core.exceptions import IntegrityError
from sqlastack.core.exceptions import InvalidConnectionString
from sqlastack.core.exceptions import MissingDatabaseURL
from sqlastack.core.exceptions import ProgrammingError
from sqlastack.core.exceptions import QueryError
from sqlastack.core.exceptions import RollbackFailed
from sqlastack.core.exceptions import SQLAStackError
from sqlastack.core.exceptions import TransactionError
from sqlastack.core.exceptions import UnknownDatabase
from sqlastack.core.exceptions import ZopeNotAvailable
from sqlastack.core.exceptions import translate_exception
import inspect
import sqlalchemy.exc
import sqlastack.core.exceptions as exc_mod


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
    assert issubclass(ZopeNotAvailable, ConfigurationError)
    assert issubclass(UnknownDatabase, ConfigurationError)


def test_hierarchy_transaction():
    assert issubclass(TransactionError, SQLAStackError)
    assert issubclass(CommitFailed, TransactionError)
    assert issubclass(RollbackFailed, TransactionError)


def test_hierarchy_query():
    assert issubclass(QueryError, SQLAStackError)
    assert issubclass(IntegrityError, QueryError)
    assert issubclass(DataError, QueryError)
    assert issubclass(ProgrammingError, QueryError)


def test_speculative_classes_removed():
    """Nie geraiste Klassen (Review 2026-09-18) existieren nicht mehr."""
    for name in (
        "ConnectionError",
        "ConnectionTimeout",
        "ConnectionRefused",
        "PoolExhausted",
        "TwoPhaseCommitFailed",
        "MigrationError",
        "MigrationFailed",
        "MigrationConflict",
    ):
        assert not hasattr(exc_mod, name), f"{name} should be removed"


def test_all_exceptions_are_sqlastack_error():
    """Every exception class DEFINED in the module is a SQLAStackError."""
    for name, obj in inspect.getmembers(exc_mod, inspect.isclass):
        if not issubclass(obj, Exception):
            continue
        if obj.__module__ != exc_mod.__name__:
            continue
        assert issubclass(obj, SQLAStackError), f"{name} is not a SQLAStackError"


def test_translate_integrity():
    orig = sqlalchemy.exc.IntegrityError("stmt", {}, Exception("dup"))
    err = translate_exception(orig)
    assert isinstance(err, IntegrityError)
    assert err.original is orig


def test_translate_data_error():
    orig = sqlalchemy.exc.DataError("stmt", {}, Exception("bad"))
    assert isinstance(translate_exception(orig), DataError)


def test_translate_programming_error():
    orig = sqlalchemy.exc.ProgrammingError("stmt", {}, Exception("syntax"))
    assert isinstance(translate_exception(orig), ProgrammingError)


def test_translate_fallback_is_commit_failed():
    orig = sqlalchemy.exc.OperationalError("stmt", {}, Exception("boom"))
    assert isinstance(translate_exception(orig), CommitFailed)
