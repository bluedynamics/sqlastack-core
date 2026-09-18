"""Tests for the shared pytest fixtures (schema handling, registry reuse)."""

from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Field
from sqlmodel import SQLModel


class SchemaItem(SQLModel, table=True):
    __tablename__ = "test_schema_item"
    __table_args__ = {"schema": "stest"}

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)


def test_schema_qualified_table_roundtrip(pg_registry):
    with pg_registry.session_scope("fh") as session:
        session.add(SchemaItem(name="in-schema"))

    with pg_registry.session_scope("fh") as session:
        rows = session.query(SchemaItem).all()
        assert [r.name for r in rows] == ["in-schema"]


def test_truncate_cleaned_schema_qualified_table(pg_registry):
    """Läuft NACH dem Roundtrip-Test: die autouse-Truncate-Fixture muss die
    schema-qualifizierte Tabelle geleert haben."""
    with pg_registry.session_scope("fh") as session:
        count = session.execute(
            text('SELECT COUNT(*) FROM "stest"."test_schema_item"')
        ).scalar()
        assert count == 0


def test_pg_registry_reuses_shared_engine(pg_registry, pg_engine):
    assert pg_registry.session_factory("fh").engine is pg_engine
