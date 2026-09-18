"""Tests for the session factory."""

from __future__ import annotations

import pytest
from sqlmodel import Field
from sqlmodel import SQLModel

from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.exceptions import ConfigurationError
from sqlastack.core.exceptions import IntegrityError
from sqlastack.core.session import SessionFactory


# Test-only model
class Item(SQLModel, table=True):
    __tablename__ = "test_item"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    code: str = Field(max_length=50, unique=True)


@pytest.fixture
def factory(pg_engine):
    factory = SessionFactory(engine=pg_engine)
    yield factory
    factory.remove_zope_session()


def test_factory_init_with_engine(factory):
    assert factory.engine is not None


def test_factory_init_with_config(pg_config: SQLAStackConfig):
    factory = SessionFactory(config=pg_config)
    assert factory.engine is not None
    factory.dispose()


def test_factory_init_without_engine_or_config_raises():
    with pytest.raises(ConfigurationError):
        SessionFactory()


def test_create_standalone_session(factory):
    session = factory.create()
    assert session is not None
    session.close()


def test_session_scope_crud(factory):
    # Create
    with factory.session_scope() as session:
        item = Item(name="Widget", code="W001")
        session.add(item)

    # Read
    with factory.session_scope() as session:
        loaded = session.get(Item, 1)
        assert loaded is not None
        assert loaded.name == "Widget"
        assert loaded.code == "W001"

    # Update
    with factory.session_scope() as session:
        loaded = session.get(Item, 1)
        loaded.name = "Updated Widget"

    with factory.session_scope() as session:
        loaded = session.get(Item, 1)
        assert loaded.name == "Updated Widget"

    # Delete
    with factory.session_scope() as session:
        loaded = session.get(Item, 1)
        session.delete(loaded)

    with factory.session_scope() as session:
        loaded = session.get(Item, 1)
        assert loaded is None


def test_session_scope_rollback_on_exception(factory):
    with factory.session_scope() as session:
        session.add(Item(name="Existing", code="UNIQUE1"))

    with pytest.raises(IntegrityError):
        with factory.session_scope() as session:
            session.add(Item(name="Duplicate", code="UNIQUE1"))

    # Original record should still be there
    with factory.session_scope() as session:
        items = session.query(Item).all()
        assert len(items) == 1
        assert items[0].name == "Existing"


def test_session_scope_rollback_on_app_exception(factory):
    """Non-SQLAlchemy exceptions also trigger rollback."""
    with pytest.raises(ValueError, match="app error"):
        with factory.session_scope() as session:
            session.add(Item(name="Ghost", code="GHOST"))
            raise ValueError("app error")

    with factory.session_scope() as session:
        items = session.query(Item).all()
        assert len(items) == 0


def test_factory_dispose(pg_config: SQLAStackConfig):
    factory = SessionFactory(config=pg_config)
    factory.dispose()
    # Should not raise; second dispose is also safe
    factory.dispose()
