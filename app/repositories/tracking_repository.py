"""SQLAlchemy adapter for :class:`~app.domain.repositories.TrackingRepository`.

Maps between the four ORM log tables and their pure-domain ``Logged*`` read
models. Reads are always user-scoped and support an optional half-open
``[start, end)`` window on ``logged_at`` (used both for history listings and for
the per-day analytics buckets), returned newest first. Writes ``flush`` — not
``commit`` — so the enclosing transaction stays owned by the caller/session.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import ExerciseLog, FoodLog, TrackingLog, WaterLog, WeightLog
from app.domain.enums import MealType
from app.domain.tracking import (
    FoodEntry,
    LoggedExercise,
    LoggedFood,
    LoggedWater,
    LoggedWeight,
    WaterEntry,
    WeightEntry,
)
from app.logging_config import get_logger

logger = get_logger(__name__)

# Generic over the four concrete tracking-log tables (all share id/user_id/logged_at).
LogT = TypeVar("LogT", bound=TrackingLog)


# --- row -> domain mappers -------------------------------------------------


def _weight_to_domain(row: WeightLog) -> LoggedWeight:
    return LoggedWeight(id=row.id, logged_at=row.logged_at, weight_kg=row.weight_kg, note=row.note)


def _water_to_domain(row: WaterLog) -> LoggedWater:
    return LoggedWater(id=row.id, logged_at=row.logged_at, volume_ml=row.volume_ml)


def _food_to_domain(row: FoodLog) -> LoggedFood:
    return LoggedFood(
        id=row.id,
        logged_at=row.logged_at,
        name=row.name,
        meal=MealType(row.meal) if row.meal is not None else None,
        calories_kcal=row.calories_kcal,
        protein_g=row.protein_g,
        carbs_g=row.carbs_g,
        fat_g=row.fat_g,
    )


def _exercise_to_domain(row: ExerciseLog) -> LoggedExercise:
    return LoggedExercise(
        id=row.id,
        logged_at=row.logged_at,
        exercise=row.exercise,
        duration_min=row.duration_min,
        met=row.met,
        calories_burned_kcal=row.calories_burned_kcal,
    )


class SqlAlchemyTrackingRepository:
    """Concrete :class:`TrackingRepository` backed by a SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- generic helpers -----------------------------------------------------
    def _persist(self, row: object) -> None:
        """Add and flush a new row so its identity is assigned."""
        self._session.add(row)
        self._session.flush()

    def _window(
        self,
        stmt: Select[tuple[LogT]],
        model: type[LogT],
        start: datetime | None,
        end: datetime | None,
    ) -> Select[tuple[LogT]]:
        """Apply an optional half-open ``[start, end)`` filter and newest-first order."""
        if start is not None:
            stmt = stmt.where(model.logged_at >= start)
        if end is not None:
            stmt = stmt.where(model.logged_at < end)
        return stmt.order_by(model.logged_at.desc(), model.id.desc())

    def _delete(self, model: type[LogT], user_id: int, log_id: int) -> bool:
        """Delete a user-scoped row by id; return whether a row was removed."""
        stmt = select(model).where(model.id == log_id, model.user_id == user_id)
        row = self._session.scalars(stmt).one_or_none()
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    # -- weight --------------------------------------------------------------
    def add_weight(self, user_id: int, entry: WeightEntry, logged_at: datetime) -> LoggedWeight:
        row = WeightLog(
            user_id=user_id,
            logged_at=logged_at,
            weight_kg=entry.weight_kg,
            note=entry.note,
        )
        self._persist(row)
        logger.info("weight_logged id=%d user_id=%d", row.id, user_id)
        return _weight_to_domain(row)

    def list_weights(
        self,
        user_id: int,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[LoggedWeight]:
        stmt = self._window(
            select(WeightLog).where(WeightLog.user_id == user_id), WeightLog, start, end
        )
        return [_weight_to_domain(r) for r in self._session.scalars(stmt)]

    def delete_weight(self, user_id: int, log_id: int) -> bool:
        return self._delete(WeightLog, user_id, log_id)

    # -- water ---------------------------------------------------------------
    def add_water(self, user_id: int, entry: WaterEntry, logged_at: datetime) -> LoggedWater:
        row = WaterLog(user_id=user_id, logged_at=logged_at, volume_ml=entry.volume_ml)
        self._persist(row)
        logger.info("water_logged id=%d user_id=%d", row.id, user_id)
        return _water_to_domain(row)

    def list_waters(
        self,
        user_id: int,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[LoggedWater]:
        stmt = self._window(
            select(WaterLog).where(WaterLog.user_id == user_id), WaterLog, start, end
        )
        return [_water_to_domain(r) for r in self._session.scalars(stmt)]

    def delete_water(self, user_id: int, log_id: int) -> bool:
        return self._delete(WaterLog, user_id, log_id)

    # -- food ----------------------------------------------------------------
    def add_food(self, user_id: int, entry: FoodEntry, logged_at: datetime) -> LoggedFood:
        row = FoodLog(
            user_id=user_id,
            logged_at=logged_at,
            name=entry.name,
            meal=entry.meal.value if entry.meal is not None else None,
            calories_kcal=entry.calories_kcal,
            protein_g=entry.protein_g,
            carbs_g=entry.carbs_g,
            fat_g=entry.fat_g,
        )
        self._persist(row)
        logger.info("food_logged id=%d user_id=%d", row.id, user_id)
        return _food_to_domain(row)

    def list_foods(
        self,
        user_id: int,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[LoggedFood]:
        stmt = self._window(select(FoodLog).where(FoodLog.user_id == user_id), FoodLog, start, end)
        return [_food_to_domain(r) for r in self._session.scalars(stmt)]

    def delete_food(self, user_id: int, log_id: int) -> bool:
        return self._delete(FoodLog, user_id, log_id)

    # -- exercise ------------------------------------------------------------
    def add_exercise(
        self,
        user_id: int,
        *,
        exercise: str,
        duration_min: float,
        met: float,
        calories_burned_kcal: float,
        logged_at: datetime,
    ) -> LoggedExercise:
        row = ExerciseLog(
            user_id=user_id,
            logged_at=logged_at,
            exercise=exercise,
            duration_min=duration_min,
            met=met,
            calories_burned_kcal=calories_burned_kcal,
        )
        self._persist(row)
        logger.info("exercise_logged id=%d user_id=%d", row.id, user_id)
        return _exercise_to_domain(row)

    def list_exercises(
        self,
        user_id: int,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[LoggedExercise]:
        stmt = self._window(
            select(ExerciseLog).where(ExerciseLog.user_id == user_id),
            ExerciseLog,
            start,
            end,
        )
        return [_exercise_to_domain(r) for r in self._session.scalars(stmt)]

    def delete_exercise(self, user_id: int, log_id: int) -> bool:
        return self._delete(ExerciseLog, user_id, log_id)
