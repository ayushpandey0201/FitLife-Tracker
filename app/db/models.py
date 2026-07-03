"""ORM models (persistence representation).

These mirror the *scalar* fields of the domain :class:`app.domain.models.UserProfile`
plus a surrogate primary key and audit timestamps. They are deliberately kept
separate from the domain model: the domain stays a pure pydantic value object,
while persistence concerns (identity, timestamps, column types) live here.

Enums are stored as their ``StrEnum`` string values in plain ``String`` columns —
portable across Postgres and SQLite, with no database-level enum type to migrate.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserProfileRecord(Base):
    """A persisted user profile (the input to the nutrition engine)."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    target_weight_kg: Mapped[float] = mapped_column(Float, nullable=False)

    # Enum values persisted as strings (see module docstring).
    sex: Mapped[str] = mapped_column(String(16), nullable=False)
    activity_level: Mapped[str] = mapped_column(String(16), nullable=False)
    diet_preference: Mapped[str] = mapped_column(String(16), nullable=False)

    weeks_to_target: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
