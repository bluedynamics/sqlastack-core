"""Reusable mixins for SQLModel models.

All columns are declared via ``sa_type``/``sa_column_kwargs`` (NOT
``sa_column=Column(...)``): a shared Column instance can only be attached to
one Table, which made the mixins single-use (review 2026-09-18). This form
lets SQLModel build a fresh Column per inheriting model.
"""

from __future__ import annotations

from sqlalchemy import DateTime
from sqlalchemy import func
from sqlmodel import Field
import datetime


class TimestampMixin:
    """Adds timezone-aware created_at and updated_at with server defaults."""

    created_at: datetime.datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now(), "nullable": False},
    )
    updated_at: datetime.datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(),
            "nullable": False,
        },
    )


class SoftDeleteMixin:
    """Adds soft-delete support via timezone-aware deleted_at timestamp."""

    deleted_at: datetime.datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = datetime.datetime.now(datetime.UTC)

    def restore(self) -> None:
        self.deleted_at = None


class AuditMixin:
    """Adds created_by and updated_by columns for audit tracking."""

    created_by: str | None = Field(default=None, max_length=255)
    updated_by: str | None = Field(default=None, max_length=255)
