"""Declarative base for all ORM models.

A single :class:`Base` carries the shared ``MetaData`` (so Alembic can autogenerate
migrations from ``Base.metadata``) and an explicit naming convention. Deterministic
constraint/index names make migrations stable and diffs reviewable across backends.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Explicit naming convention → predictable, portable constraint/index names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Common declarative base shared by every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
