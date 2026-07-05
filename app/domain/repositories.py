"""Repository ports (interfaces) — the persistence seam.

These are the *ports* of the hexagonal/clean architecture: abstract contracts
the domain and application layers depend on, with concrete adapters (SQLAlchemy,
in-memory, ...) supplied from the outside. Declaring them here — with no import
of any storage technology — keeps the domain free of infrastructure while making
persistence swappable and trivially fakeable in tests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from app.domain.models import StoredProfile, UserProfile
from app.domain.tracking import (
    FoodEntry,
    LoggedExercise,
    LoggedFood,
    LoggedWater,
    LoggedWeight,
    WaterEntry,
    WeightEntry,
)


@runtime_checkable
class ProfileRepository(Protocol):
    """Persistence contract for :class:`~app.domain.models.UserProfile` records.

    All reads are scoped to an owning user: a profile belongs to exactly one
    account, and one user may accumulate several profiles over time (the most
    recent being their current one).
    """

    def add(self, user_id: int, profile: UserProfile) -> StoredProfile:
        """Persist a new profile for ``user_id`` and return it with its identity."""
        ...

    def get_for_user(self, user_id: int, profile_id: int) -> StoredProfile | None:
        """Return the user's profile with ``profile_id``, or ``None`` if absent."""
        ...

    def get_current(self, user_id: int) -> StoredProfile | None:
        """Return the user's most recently created profile, or ``None``."""
        ...

    def list_for_user(self, user_id: int) -> list[StoredProfile]:
        """Return all of the user's profiles, newest first (history)."""
        ...


@runtime_checkable
class TrackingRepository(Protocol):
    """Persistence contract for a user's tracking logs.

    One method group per tracked quantity (weight, water, food, exercise). Adds
    take the validated domain *input* plus the resolved ``logged_at`` (the app
    layer owns the clock); exercise adds also carry the service-derived ``met``
    and ``calories_burned_kcal``. Every read is user-scoped and accepts an
    optional half-open ``[start, end)`` time window, returned newest first.
    """

    # -- weight --------------------------------------------------------------
    def add_weight(self, user_id: int, entry: WeightEntry, logged_at: datetime) -> LoggedWeight: ...

    def list_weights(
        self,
        user_id: int,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[LoggedWeight]: ...

    def delete_weight(self, user_id: int, log_id: int) -> bool: ...

    # -- water ---------------------------------------------------------------
    def add_water(self, user_id: int, entry: WaterEntry, logged_at: datetime) -> LoggedWater: ...

    def list_waters(
        self,
        user_id: int,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[LoggedWater]: ...

    def delete_water(self, user_id: int, log_id: int) -> bool: ...

    # -- food ----------------------------------------------------------------
    def add_food(self, user_id: int, entry: FoodEntry, logged_at: datetime) -> LoggedFood: ...

    def list_foods(
        self,
        user_id: int,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[LoggedFood]: ...

    def delete_food(self, user_id: int, log_id: int) -> bool: ...

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
    ) -> LoggedExercise: ...

    def list_exercises(
        self,
        user_id: int,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[LoggedExercise]: ...

    def delete_exercise(self, user_id: int, log_id: int) -> bool: ...
