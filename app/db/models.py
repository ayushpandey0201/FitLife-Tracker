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

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
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
    weight_logs: Mapped[list[WeightLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    water_logs: Mapped[list[WaterLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    food_logs: Mapped[list[FoodLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    exercise_logs: Mapped[list[ExerciseLog]] = relationship(
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


# ---------------------------------------------------------------------------
# Tracking logs (Phase 5)
#
# Four user-owned, time-stamped tables — one per tracked quantity. Each shares
# id / user_id / ``logged_at`` (server-defaulted to now, but caller-overridable
# to back-date) via the abstract ``TrackingLog`` base, plus a composite
# ``(user_id, logged_at)`` index, because every read is "this user's entries
# within a time window", newest first.
# ---------------------------------------------------------------------------


class TrackingLog(TimestampMixin, Base):
    """Abstract base for user-owned, time-stamped tracking rows.

    ``__abstract__`` means no table of its own: SQLAlchemy copies these columns
    onto each concrete subclass. Sharing them here removes four-way duplication
    and gives a single typed base the repository can be generic over.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WeightLog(TrackingLog):
    """A recorded body-weight measurement."""

    __tablename__ = "weight_logs"
    __table_args__ = (Index("ix_weight_logs_user_logged_at", "user_id", "logged_at"),)

    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(String(280), nullable=True)

    user: Mapped[User] = relationship(back_populates="weight_logs")


class WaterLog(TrackingLog):
    """A recorded water-intake measurement."""

    __tablename__ = "water_logs"
    __table_args__ = (Index("ix_water_logs_user_logged_at", "user_id", "logged_at"),)

    volume_ml: Mapped[float] = mapped_column(Float, nullable=False)

    user: Mapped[User] = relationship(back_populates="water_logs")


class FoodLog(TrackingLog):
    """A recorded food/meal with its nutrition as consumed."""

    __tablename__ = "food_logs"
    __table_args__ = (Index("ix_food_logs_user_logged_at", "user_id", "logged_at"),)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Enum value persisted as a string, or NULL when the meal is unspecified.
    meal: Mapped[str | None] = mapped_column(String(16), nullable=True)
    calories_kcal: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)

    user: Mapped[User] = relationship(back_populates="food_logs")


class ExerciseLog(TrackingLog):
    """A recorded exercise session and its derived energy expenditure.

    ``met`` and ``calories_burned_kcal`` are computed at log time (from the
    catalogue MET and the user's then-current weight) and stored, so historical
    entries stay stable even if the catalogue or the user's weight later change.
    """

    __tablename__ = "exercise_logs"
    __table_args__ = (Index("ix_exercise_logs_user_logged_at", "user_id", "logged_at"),)

    exercise: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_min: Mapped[float] = mapped_column(Float, nullable=False)
    met: Mapped[float] = mapped_column(Float, nullable=False)
    calories_burned_kcal: Mapped[float] = mapped_column(Float, nullable=False)

    user: Mapped[User] = relationship(back_populates="exercise_logs")
