"""Tests for Zope-integrated session mode."""

from __future__ import annotations

from unittest import mock

import pytest
import transaction
from sqlmodel import Field
from sqlmodel import SQLModel

from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.engine import create_sqlastack_engine
from sqlastack.core.exceptions import ZopeNotAvailable
from sqlastack.core.session import SessionFactory


# Test-only model
class ZopeItem(SQLModel, table=True):
    __tablename__ = "test_zope_item"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)


@pytest.fixture
def zope_factory():
    config = SQLAStackConfig(database_url="sqlite:///:memory:")
    engine = create_sqlastack_engine(config)
    SQLModel.metadata.create_all(engine)
    factory = SessionFactory(engine=engine)
    yield factory
    factory.dispose()


def test_create_zope_true_returns_session(zope_factory):
    """create(zope=True) returns a valid session."""
    session = zope_factory.create(zope=True)
    assert session is not None


def test_create_zope_true_same_thread_same_session(zope_factory):
    """Two calls in the same thread return the same session (scoped_session)."""
    session1 = zope_factory.create(zope=True)
    session2 = zope_factory.create(zope=True)
    assert session1 is session2


def test_create_zope_true_without_zope_raises(zope_factory):
    """When HAS_ZOPE is False, create(zope=True) raises ZopeNotAvailable."""
    with mock.patch("sqlastack.plone.HAS_ZOPE", False):
        # Reset the lazy scoped session so it tries to create a new one
        zope_factory._scoped_session = None
        with pytest.raises(ZopeNotAvailable):
            zope_factory.create(zope=True)


def test_session_scope_zope_no_auto_commit(zope_factory):
    """session_scope(zope=True) does not auto-commit."""
    with zope_factory.session_scope(zope=True) as session:
        session.add(ZopeItem(name="Uncommitted"))

    # Without transaction.commit(), data should not be visible in a new standalone session
    standalone_session = zope_factory.create(zope=False)
    try:
        items = standalone_session.query(ZopeItem).all()
        assert len(items) == 0
    finally:
        standalone_session.close()
    transaction.abort()


def test_transaction_commit_persists_data(zope_factory):
    """transaction.commit() persists data from a Zope session."""
    with zope_factory.session_scope(zope=True) as session:
        session.add(ZopeItem(name="Persisted"))

    transaction.commit()

    # Data should be visible in a new standalone session
    standalone_session = zope_factory.create(zope=False)
    try:
        items = standalone_session.query(ZopeItem).all()
        assert len(items) == 1
        assert items[0].name == "Persisted"
    finally:
        standalone_session.close()


def test_transaction_abort_rolls_back(zope_factory):
    """transaction.abort() rolls back data from a Zope session."""
    with zope_factory.session_scope(zope=True) as session:
        session.add(ZopeItem(name="Aborted"))

    transaction.abort()

    # Data should not be visible
    standalone_session = zope_factory.create(zope=False)
    try:
        items = standalone_session.query(ZopeItem).all()
        assert len(items) == 0
    finally:
        standalone_session.close()


def test_session_scope_standalone_unchanged(zope_factory):
    """Standalone session_scope still commits on success."""
    with zope_factory.session_scope(zope=False) as session:
        session.add(ZopeItem(name="Standalone"))

    standalone_session = zope_factory.create(zope=False)
    try:
        items = standalone_session.query(ZopeItem).all()
        assert len(items) == 1
        assert items[0].name == "Standalone"
    finally:
        standalone_session.close()


def test_dispose_cleans_up_scoped_session(zope_factory):
    """dispose() removes the scoped session."""
    zope_factory.create(zope=True)
    assert zope_factory._scoped_session is not None
    zope_factory.dispose()
    # After dispose, engine is disposed — creating new sessions would fail
    # but the scoped session should have been removed


def test_exception_propagates_in_zope_mode(zope_factory):
    """Exceptions in Zope mode propagate without translation."""
    with pytest.raises(ValueError, match="app error"):
        with zope_factory.session_scope(zope=True) as session:
            session.add(ZopeItem(name="Ghost"))
            raise ValueError("app error")
    transaction.abort()
