"""Tests for DatabaseRegistry (named SessionFactories) against PostgreSQL."""

from __future__ import annotations

from sqlalchemy import text
from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.exceptions import UnknownDatabase
from sqlastack.core.registry import DatabaseRegistry
from unittest import mock
import pytest


def test_unknown_name_raises(pg_config: SQLAStackConfig):
    registry = DatabaseRegistry({"fh": pg_config})
    with pytest.raises(UnknownDatabase, match="owned"):
        registry.session_factory("owned")


def test_names_are_sorted(pg_config: SQLAStackConfig):
    registry = DatabaseRegistry({"fh": pg_config, "owned": pg_config})
    assert registry.names() == ["fh", "owned"]


def test_session_factory_is_cached(pg_config: SQLAStackConfig):
    registry = DatabaseRegistry({"fh": pg_config})
    f1 = registry.session_factory("fh")
    f2 = registry.session_factory("fh")
    assert f1 is f2
    registry.dispose_all()


def test_session_scope_executes_query(pg_config: SQLAStackConfig):
    registry = DatabaseRegistry({"fh": pg_config})
    with registry.session_scope("fh") as session:
        assert session.execute(text("SELECT 1")).scalar() == 1
    registry.dispose_all()


def test_from_env_discovers_named_databases(monkeypatch, pg_url: str):
    monkeypatch.setenv("SQLASTACK_FH_URL", pg_url)
    registry = DatabaseRegistry.from_env()
    assert "fh" in registry.names()
    registry.dispose_all()


def test_register_disposes_evicted_factory(pg_config: SQLAStackConfig):
    registry = DatabaseRegistry({"fh": pg_config})
    factory = registry.session_factory("fh")  # create + cache it
    with mock.patch.object(factory, "dispose") as disposed:
        registry.register("fh", pg_config)  # replace -> should dispose old factory
    disposed.assert_called_once()
    registry.dispose_all()
