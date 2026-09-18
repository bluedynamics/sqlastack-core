"""Tests for the Zope-integrated session mode (PostgreSQL)."""

from __future__ import annotations

from sqlastack.core.exceptions import ZopeNotAvailable
from sqlastack.core.session import SessionFactory
from sqlmodel import Field
from sqlmodel import SQLModel
from unittest import mock
import pytest
import transaction


class ZopeItem(SQLModel, table=True):
    __tablename__ = "test_zope_item"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)


@pytest.fixture
def zope_factory(pg_engine):
    factory = SessionFactory(engine=pg_engine)
    yield factory
    factory.remove_zope_session()
    transaction.abort()


def test_zope_session_returns_shared_proxy(zope_factory):
    s1 = zope_factory.zope_session()
    s2 = zope_factory.zope_session()
    assert s1 is s2


def test_zope_session_checks_availability_every_call(zope_factory):
    zope_factory.zope_session()  # lazily created
    with mock.patch("sqlastack.plone.HAS_ZOPE", False):
        with pytest.raises(ZopeNotAvailable):
            zope_factory.zope_session()


def test_create_has_no_zope_parameter(zope_factory):
    with pytest.raises(TypeError):
        zope_factory.create(zope=True)  # type: ignore[call-arg]


def test_transaction_commit_persists_data(zope_factory):
    session = zope_factory.zope_session()
    session.add(ZopeItem(name="Persisted"))
    transaction.commit()

    standalone = zope_factory.create()
    try:
        items = standalone.query(ZopeItem).all()
        assert len(items) == 1
        assert items[0].name == "Persisted"
    finally:
        standalone.close()


def test_transaction_abort_rolls_back(zope_factory):
    session = zope_factory.zope_session()
    session.add(ZopeItem(name="Aborted"))
    transaction.abort()

    standalone = zope_factory.create()
    try:
        assert standalone.query(ZopeItem).all() == []
    finally:
        standalone.close()


def test_failed_request_does_not_bleed_after_remove(zope_factory):
    """Das Plan-2-Muster: Fehler in Request 1, Teardown, Request 2 ist sauber."""
    session = zope_factory.zope_session()
    session.add(ZopeItem(name="Ghost"))
    # Request 1 schlägt fehl: der Publisher würde abort() rufen, wir simulieren das
    transaction.abort()
    zope_factory.remove_zope_session()

    # Request 2 im selben Thread: keine Ghost-Row, frische Session
    session2 = zope_factory.zope_session()
    assert session2.query(ZopeItem).all() == []
    session2.add(ZopeItem(name="Clean"))
    transaction.commit()
    standalone = zope_factory.create()
    try:
        names = [i.name for i in standalone.query(ZopeItem).all()]
        assert names == ["Clean"]
    finally:
        standalone.close()


def test_remove_zope_session_without_creation_is_noop(zope_factory):
    zope_factory.remove_zope_session()  # must not raise


def test_session_scope_is_standalone_only(zope_factory):
    with pytest.raises(TypeError):
        with zope_factory.session_scope(zope=True):  # type: ignore[call-arg]
            pass
