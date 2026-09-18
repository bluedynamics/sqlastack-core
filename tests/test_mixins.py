"""Tests for the reusable mixins (PostgreSQL)."""

from __future__ import annotations

from sqlastack.core.mixins import AuditMixin
from sqlastack.core.mixins import SoftDeleteMixin
from sqlastack.core.mixins import TimestampMixin
from sqlmodel import Field
from sqlmodel import Session
from sqlmodel import SQLModel
import datetime


class MixedItemA(TimestampMixin, SoftDeleteMixin, AuditMixin, SQLModel, table=True):
    __tablename__ = "test_mixed_item_a"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)


class MixedItemB(TimestampMixin, SoftDeleteMixin, AuditMixin, SQLModel, table=True):
    """Zweites Modell mit denselben Mixins — Regression für das
    sa_column-Sharing (Review 2026-09-18: ArgumentError beim zweiten Modell)."""

    __tablename__ = "test_mixed_item_b"

    id: int | None = Field(default=None, primary_key=True)
    label: str = Field(max_length=100)


def test_mixins_usable_by_multiple_models():
    assert MixedItemA.__table__.c.created_at is not MixedItemB.__table__.c.created_at


def test_timestamp_mixin_defaults_are_timezone_aware(pg_engine):
    with Session(pg_engine) as session:
        item = MixedItemA(name="Timestamped")
        session.add(item)
        session.commit()
        session.refresh(item)

        assert item.created_at is not None
        assert item.created_at.tzinfo is not None
        assert item.updated_at is not None
        assert item.updated_at.tzinfo is not None


def test_second_model_roundtrip(pg_engine):
    with Session(pg_engine) as session:
        item = MixedItemB(label="Second")
        session.add(item)
        session.commit()
        session.refresh(item)
        assert item.created_at is not None


def test_soft_delete_mixin(pg_engine):
    with Session(pg_engine) as session:
        item = MixedItemA(name="Deletable")
        session.add(item)
        session.commit()
        session.refresh(item)

        assert item.is_deleted is False

        item.soft_delete()
        session.commit()
        session.refresh(item)
        assert item.is_deleted is True
        assert item.deleted_at is not None
        assert item.deleted_at.tzinfo is not None
        # aware vs aware — kein TypeError mehr (Review-Finding)
        assert item.deleted_at <= datetime.datetime.now(datetime.UTC)

        item.restore()
        session.commit()
        session.refresh(item)
        assert item.is_deleted is False


def test_audit_mixin(pg_engine):
    with Session(pg_engine) as session:
        item = MixedItemA(name="Auditable", created_by="admin", updated_by="admin")
        session.add(item)
        session.commit()
        session.refresh(item)
        assert item.created_by == "admin"
        assert item.updated_by == "admin"
