"""Tests for the process-wide registry lifecycle in sqlastack.plone."""

from __future__ import annotations

from sqlastack.plone import close_zope_sessions
from sqlastack.plone import get_registry
from sqlastack.plone import reset_registry
from sqlmodel import Field
from sqlmodel import SQLModel
import pytest
import transaction


class IntegrationItem(SQLModel, table=True):
    __tablename__ = "test_integration_item"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)


@pytest.fixture
def forms_env(pg_url, pg_engine, monkeypatch):
    """Configure a 'forms' database from env and guarantee teardown."""
    monkeypatch.setenv("SQLASTACK_FORMS_URL", pg_url)
    reset_registry()
    yield
    transaction.abort()
    reset_registry()


def test_get_registry_is_singleton_and_warmed(forms_env):
    registry = get_registry()
    assert registry is get_registry()
    assert "forms" in registry.names()
    # warm_up: factory exists without any session use
    assert "forms" in registry._factories


def test_reset_registry_forgets_instance(forms_env):
    first = get_registry()
    reset_registry()
    assert get_registry() is not first


def test_close_zope_sessions_without_registry_is_noop():
    reset_registry()
    close_zope_sessions(None)  # must not raise, must not build a registry


def test_request_cycle_no_bleed(forms_env):
    """Fehlgeschlagener 'Request' + Subscriber-Teardown -> nächster ist sauber."""
    registry = get_registry()
    session = registry.zope_session("forms")
    session.add(IntegrationItem(name="Ghost"))
    transaction.abort()
    close_zope_sessions(None)  # what the IPubFailure subscriber does

    session2 = get_registry().zope_session("forms")
    assert session2.query(IntegrationItem).all() == []
    transaction.abort()
