"""Tests for DatabaseRegistry (named SessionFactories) against PostgreSQL."""

from __future__ import annotations

from sqlalchemy import text
from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.exceptions import ConfigurationError
from sqlastack.core.exceptions import UnknownDatabase
from sqlastack.core.registry import DatabaseRegistry
from sqlastack.core.session import SessionFactory
from sqlmodel import Field
from sqlmodel import SQLModel
import pytest
import transaction


class RegistryItem(SQLModel, table=True):
    __tablename__ = "test_registry_item"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)


@pytest.fixture
def registry(pg_config: SQLAStackConfig):
    registry = DatabaseRegistry({"fh": pg_config})
    yield registry
    registry.dispose_all()


def test_unknown_name_raises(registry):
    with pytest.raises(UnknownDatabase, match="owned"):
        registry.session_factory("owned")


def test_names_are_sorted(pg_config: SQLAStackConfig):
    registry = DatabaseRegistry({"fh": pg_config, "owned": pg_config})
    assert registry.names() == ["fh", "owned"]


def test_names_are_normalized_to_lowercase(pg_config: SQLAStackConfig):
    registry = DatabaseRegistry()
    registry.register("FH", pg_config)
    assert registry.names() == ["fh"]
    assert registry.session_factory("Fh") is registry.session_factory("fh")
    registry.dispose_all()


def test_invalid_name_rejected(pg_config: SQLAStackConfig):
    registry = DatabaseRegistry()
    with pytest.raises(ConfigurationError, match="my_db"):
        registry.register("my_db", pg_config)


def test_session_factory_is_cached(registry):
    assert registry.session_factory("fh") is registry.session_factory("fh")


def test_session_scope_executes_query(registry):
    with registry.session_scope("fh") as session:
        assert session.execute(text("SELECT 1")).scalar() == 1


def test_from_env_discovers_named_databases(monkeypatch, pg_url: str):
    monkeypatch.setenv("SQLASTACK_FH_URL", pg_url)
    registry = DatabaseRegistry.from_env()
    assert "fh" in registry.names()
    registry.dispose_all()


def test_register_refuses_replacing_live_factory(registry, pg_config):
    registry.session_factory("fh")  # create + cache
    with pytest.raises(ConfigurationError, match="in use"):
        registry.register("fh", pg_config)


def test_register_replaces_config_before_factory_creation(registry, pg_config):
    registry.register("fh", pg_config)  # no factory yet -> fine
    assert registry.names() == ["fh"]


def test_register_factory_injects_prebuilt(pg_engine):
    registry = DatabaseRegistry()
    registry.register_factory("fh", SessionFactory(engine=pg_engine))
    with registry.session_scope("fh") as session:
        assert session.execute(text("SELECT 1")).scalar() == 1
    # kein dispose_all: der Engine gehört der pg_engine-Fixture


def test_warm_up_creates_all_factories(pg_config):
    registry = DatabaseRegistry({"fh": pg_config, "owned": pg_config})
    registry.warm_up()
    assert set(registry._factories) == {"fh", "owned"}
    registry.dispose_all()


def test_dead_session_method_removed(registry):
    assert not hasattr(registry, "session")


def test_zope_session_two_requests_no_bleed(pg_engine):
    """Plan-2-Naht: zwei sequenzielle 'Requests' gegen eine langlebige Registry."""
    registry = DatabaseRegistry()
    registry.register_factory("fh", SessionFactory(engine=pg_engine))

    # Request 1: schreibt, scheitert, Publisher aborted, Request-Ende räumt auf
    session = registry.zope_session("fh")
    session.add(RegistryItem(name="Ghost"))
    transaction.abort()
    registry.remove_zope_sessions()

    # Request 2: sieht nichts von Request 1
    session2 = registry.zope_session("fh")
    assert session2.query(RegistryItem).all() == []
    transaction.abort()
    registry.remove_zope_sessions()
