"""ORM models (persistence representation).

These mirror the *scalar* fields of the domain value objects plus surrogate keys,
foreign keys, and audit timestamps. They are deliberately kept separate from the
domain models: the domain stays pure pydantic, while persistence concerns
(identity, timestamps, relationships, column types) live here.

Enums are stored as their ``StrEnum`` string values in plain ``String`` columns —
portable across Postgres and SQLite, with no database-level enum type to migrate.
Full computed plans are stored as JSON (via SQLAlchemy's portable ``JSON`` type)
alongside a few indexed summary columns that later analytics can query directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# A decoded JSON object payload (stored in a portable JSON column).
JsonDict = dict[str, Any]


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` audit columns to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    """An authenticated account. Owns profiles, plans, and refresh tokens."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # Role string (RBAC-ready). Only "user" exists today; "admin" reserved.
    role: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profiles: Mapped[list[UserProfileRecord]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    plans: Mapped[list[PlanRecord]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserProfileRecord(TimestampMixin, Base):
    """A persisted user profile (the input to the nutrition engine).

    A user may have several over time (versioned history); the most recent is
    treated as their current profile.
    """

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

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

    user: Mapped[User] = relationship(back_populates="profiles")


class PlanRecord(TimestampMixin, Base):
    """A persisted, generated nutrition plan — historical record per user.

    Summary columns (goal, calorie target, bmi) are indexed-friendly for future
    progress analytics; the complete plan and meal plan are kept verbatim as JSON
    so the exact advice a user was given can always be reconstructed.
    """

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True
    )

    # Analytics-friendly summary columns.
    goal: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    diet_preference: Mapped[str] = mapped_column(String(16), nullable=False)
    calorie_target_kcal: Mapped[float] = mapped_column(Float, nullable=False)
    bmi: Mapped[float] = mapped_column(Float, nullable=False)

    # Full-fidelity payloads (portable JSON).
    nutrition_plan: Mapped[JsonDict] = mapped_column(JSON, nullable=False)
    meal_plan: Mapped[JsonDict] = mapped_column(JSON, nullable=False)

    user: Mapped[User] = relationship(back_populates="plans")


class RefreshToken(TimestampMixin, Base):
    """A stored, revocable refresh token (hashed; the raw token is never saved).

    Persisting refresh tokens is what makes logout and rotation possible: on
    refresh the old ``jti`` is revoked and a new token issued; on logout it is
    revoked outright.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
