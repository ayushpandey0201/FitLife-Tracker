"""Tracking service: record logs and compute progress analytics.

Orchestrates the tracking repository (and, for exercise energy, the profile
repository + exercise catalogue) and delegates all arithmetic to the pure
:mod:`app.domain.tracking` functions. Responsibilities that need the outside
world live here, not in the domain:

* resolving an omitted ``logged_at`` to "now" (UTC) — the domain has no clock;
* looking up an exercise's MET from the catalogue and the user's current weight
  to derive calories burned at log time;
* turning a calendar ``date`` into the half-open UTC window the repository reads.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.catalog import load_exercises
from app.domain.tracking import (
    DailySummary,
    ExerciseEntry,
    FoodEntry,
    LoggedExercise,
    LoggedFood,
    LoggedWater,
    LoggedWeight,
    WaterEntry,
    WeightEntry,
    WeightTrend,
    build_weight_trend,
    calories_burned,
    summarise_day,
)
from app.logging_config import get_logger
from app.repositories.profile_repository import SqlAlchemyProfileRepository
from app.repositories.tracking_repository import SqlAlchemyTrackingRepository
from app.services.exceptions import (
    LogNotFoundError,
    ProfileNotFoundError,
    UnknownExerciseError,
)

logger = get_logger(__name__)


def _day_window(day: date) -> tuple[datetime, datetime]:
    """Return the half-open ``[start, end)`` UTC datetime range covering ``day``."""
    start = datetime.combine(day, time.min, tzinfo=UTC)
    return start, start + timedelta(days=1)


def _range_window(start: date | None, end: date | None) -> tuple[datetime | None, datetime | None]:
    """Turn optional start/end *dates* into an inclusive-day UTC datetime window."""
    start_dt = datetime.combine(start, time.min, tzinfo=UTC) if start else None
    # ``end`` is inclusive of the whole day, so the exclusive bound is the next day.
    end_dt = datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC) if end else None
    return start_dt, end_dt


class TrackingService:
    """Use cases for recording tracking logs and reading progress."""

    def __init__(self, session: Session) -> None:
        self._repo = SqlAlchemyTrackingRepository(session)
        self._profiles = SqlAlchemyProfileRepository(session)

    # -- clock ---------------------------------------------------------------
    @staticmethod
    def _resolve(logged_at: datetime | None) -> datetime:
        """An explicit timestamp if given, else the current UTC time."""
        return logged_at if logged_at is not None else datetime.now(UTC)

    # -- weight --------------------------------------------------------------
    def log_weight(self, user_id: int, entry: WeightEntry) -> LoggedWeight:
        return self._repo.add_weight(user_id, entry, self._resolve(entry.logged_at))

    def list_weights(self, user_id: int) -> list[LoggedWeight]:
        return self._repo.list_weights(user_id)

    def delete_weight(self, user_id: int, log_id: int) -> None:
        if not self._repo.delete_weight(user_id, log_id):
            raise LogNotFoundError(f"weight log {log_id} not found")

    # -- water ---------------------------------------------------------------
    def log_water(self, user_id: int, entry: WaterEntry) -> LoggedWater:
        return self._repo.add_water(user_id, entry, self._resolve(entry.logged_at))

    def list_waters(self, user_id: int) -> list[LoggedWater]:
        return self._repo.list_waters(user_id)

    def delete_water(self, user_id: int, log_id: int) -> None:
        if not self._repo.delete_water(user_id, log_id):
            raise LogNotFoundError(f"water log {log_id} not found")

    # -- food ----------------------------------------------------------------
    def log_food(self, user_id: int, entry: FoodEntry) -> LoggedFood:
        return self._repo.add_food(user_id, entry, self._resolve(entry.logged_at))

    def list_foods(self, user_id: int) -> list[LoggedFood]:
        return self._repo.list_foods(user_id)

    def delete_food(self, user_id: int, log_id: int) -> None:
        if not self._repo.delete_food(user_id, log_id):
            raise LogNotFoundError(f"food log {log_id} not found")

    # -- exercise ------------------------------------------------------------
    def log_exercise(self, user_id: int, entry: ExerciseEntry) -> LoggedExercise:
        """Log an exercise, deriving energy from its MET and the user's weight.

        Requires a current profile (for body weight) and a catalogue match for
        the exercise name; raises :class:`ProfileNotFoundError` /
        :class:`UnknownExerciseError` respectively.
        """
        current = self._profiles.get_current(user_id)
        if current is None:
            raise ProfileNotFoundError("a profile is required to log exercise (for body weight)")

        met = self._lookup_met(entry.exercise)
        weight_kg = current.profile.weight_kg
        burned = calories_burned(met=met, weight_kg=weight_kg, duration_min=entry.duration_min)
        return self._repo.add_exercise(
            user_id,
            exercise=entry.exercise,
            duration_min=entry.duration_min,
            met=met,
            calories_burned_kcal=burned,
            logged_at=self._resolve(entry.logged_at),
        )

    def list_exercises(self, user_id: int) -> list[LoggedExercise]:
        return self._repo.list_exercises(user_id)

    def delete_exercise(self, user_id: int, log_id: int) -> None:
        if not self._repo.delete_exercise(user_id, log_id):
            raise LogNotFoundError(f"exercise log {log_id} not found")

    @staticmethod
    def _lookup_met(name: str) -> float:
        """Return the catalogue MET for ``name`` (case-insensitive), or raise."""
        target = name.strip().lower()
        for exercise in load_exercises():
            if exercise.name.lower() == target:
                return exercise.met
        raise UnknownExerciseError(f"unknown exercise: {name!r}")

    # -- analytics -----------------------------------------------------------
    def daily_summary(self, user_id: int, day: date) -> DailySummary:
        """Aggregate the user's food/exercise/water logs for a UTC ``day``."""
        start, end = _day_window(day)
        return summarise_day(
            day,
            foods=self._repo.list_foods(user_id, start=start, end=end),
            exercises=self._repo.list_exercises(user_id, start=start, end=end),
            waters=self._repo.list_waters(user_id, start=start, end=end),
        )

    def weight_trend(
        self, user_id: int, *, start: date | None = None, end: date | None = None
    ) -> WeightTrend:
        """Build the user's weight trend over an optional inclusive date range."""
        start_dt, end_dt = _range_window(start, end)
        entries = self._repo.list_weights(user_id, start=start_dt, end=end_dt)
        return build_weight_trend(entries)
