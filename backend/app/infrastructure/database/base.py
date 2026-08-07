"""
Infrastructure database base module.

Single source of truth for SQLAlchemy Base and reusable mixins.
All domain models MUST inherit from Base defined here.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all Atlas SQLAlchemy models."""


class TimestampMixin:
    """
    Adds created_at and updated_at audit columns to any model.

    created_at is set once on INSERT, never changes.
    updated_at is set on INSERT and every subsequent UPDATE.
    Both are timezone-aware UTC timestamps.
    """

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        default=lambda: datetime.now(timezone.utc),
    )


class SoftDeleteMixin:
    """
    Adds deleted_at soft-delete support.

    Records are NEVER physically deleted. Instead, deleted_at is set to
    the deletion timestamp. All queries should filter WHERE deleted_at IS NULL.

    Unique indexes on active records should use partial indexes:
        CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL
    """

    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark this record as deleted without removing it from the database."""
        self.deleted_at = datetime.now(timezone.utc)
