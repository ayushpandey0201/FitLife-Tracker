"""Tracking domain — logged measurements and pure analytics.

Phase 5 adds *tracking*: a user records what actually happened (weigh-ins, water,
food eaten, exercise done) so progress can be measured against the plan. As with
the rest of ``app.domain`` this module is pure — validated value objects plus
deterministic functions, no I/O and no clock. The application layer supplies the
current time, the catalogue MET value, and the user's body weight; the maths of
"calories burned" and "sum up a day" lives here where it can be tested directly.

Two shapes per log type:

* an **input** model (what a caller submits) — e.g. :class:`WeightEntry`;
* a **logged** model (input + persistence identity + resolved ``logged_at``, and,
  for exercise, the derived energy) — e.g. :class:`LoggedWeight`.

``logged_at`` is always timezone-aware; daily aggregation buckets by **UTC**
calendar date so results are deterministic regardless of server locale.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import MealType

# --- inputs (what a caller submits) ---------------------------------------


class _Entry(BaseModel):
    """Common base for log inputs: an optional caller-supplied timestamp.

    When ``logged_at`` is ``None`` the application layer resolves it to "now"
    (the domain never reads the clock). Supplying it allows back-dating entries.
    """

    model_config = ConfigDict(frozen=True)

    logged_at: datetime | None = Field(
        default=None, description="When the entry occurred; defaults to now if omitted"
    )


class WeightEntry(_Entry):
    """A body-weight measurement."""

    weight_kg: float = Field(gt=2, le=500, description="Measured weight in kg")
    note: str | None = Field(default=None, max_length=280)


class WaterEntry(_Entry):
    """A water-intake measurement."""

    volume_ml: float = Field(gt=0, le=10_000, description="Water volume in millilitres")


class FoodEntry(_Entry):
    """A logged food/meal with its nutrition (as consumed).

    Calories are stored explicitly rather than recomputed from macros: a caller
    may know the calories of a packaged item without a full macro breakdown.
    """

    name: str = Field(min_length=1, max_length=100)
    meal: MealType | None = Field(default=None, description="Which meal, if known")
    calories_kcal: float = Field(ge=0, le=10_000)
    protein_g: float = Field(default=0.0, ge=0)
    carbs_g: float = Field(default=0.0, ge=0)
    fat_g: float = Field(default=0.0, ge=0)


class ExerciseEntry(_Entry):
    """A logged exercise session. Energy is derived, not supplied by the caller."""

    exercise: str = Field(min_length=1, max_length=100, description="Catalogue name")
    duration_min: float = Field(gt=0, le=1440, description="Duration in minutes")


# --- logged records (persisted, with identity) -----------------------------


class _Logged(BaseModel):
    """Common base for persisted log records."""

    model_config = ConfigDict(frozen=True)

    id: int
    logged_at: datetime


class LoggedWeight(_Logged):
    """A persisted weight measurement."""

    weight_kg: float
    note: str | None = None


class LoggedWater(_Logged):
    """A persisted water-intake measurement."""

    volume_ml: float


class LoggedFood(_Logged):
    """A persisted food log."""

    name: str
    meal: MealType | None = None
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class LoggedExercise(_Logged):
    """A persisted exercise log, including the derived energy expenditure."""

    exercise: str
    duration_min: float
    met: float
    calories_burned_kcal: float


# --- analytics results -----------------------------------------------------


class DailySummary(BaseModel):
    """Aggregated tracking for a single UTC calendar date."""

    model_config = ConfigDict(frozen=True)

    date: date
    calories_consumed_kcal: float = Field(description="Sum of food logs")
    calories_burned_kcal: float = Field(description="Sum of exercise logs")
    net_calories_kcal: float = Field(description="consumed minus burned")
    protein_g: float
    carbs_g: float
    fat_g: float
    water_ml: float
    food_count: int
    exercise_count: int


class WeightTrend(BaseModel):
    """A body-weight series with its net change over the range (oldest → newest)."""

    model_config = ConfigDict(frozen=True)

    entries: list[LoggedWeight]
    start_kg: float | None = Field(default=None, description="Earliest weight in range")
    latest_kg: float | None = Field(default=None, description="Most recent weight")
    change_kg: float | None = Field(default=None, description="latest minus start")


# --- pure functions --------------------------------------------------------


def calories_burned(*, met: float, weight_kg: float, duration_min: float) -> float:
    """Energy expended by an activity, via the standard MET relation.

    ``kcal = MET * weight_kg * hours`` — one MET is ~1 kcal per kg per hour.
    Rounded to one decimal so stored values are stable and human-friendly.
    """
    return round(met * weight_kg * (duration_min / 60.0), 1)


def summarise_day(
    day: date,
    *,
    foods: Iterable[LoggedFood],
    exercises: Iterable[LoggedExercise],
    waters: Iterable[LoggedWater],
) -> DailySummary:
    """Aggregate a day's logs into a :class:`DailySummary`.

    The caller is expected to pass only entries for ``day``; totals are simple
    sums so the function stays trivially correct and order-independent.
    """
    foods = list(foods)
    exercises = list(exercises)
    waters = list(waters)

    consumed = round(sum(f.calories_kcal for f in foods), 1)
    burned = round(sum(e.calories_burned_kcal for e in exercises), 1)
    return DailySummary(
        date=day,
        calories_consumed_kcal=consumed,
        calories_burned_kcal=burned,
        net_calories_kcal=round(consumed - burned, 1),
        protein_g=round(sum(f.protein_g for f in foods), 1),
        carbs_g=round(sum(f.carbs_g for f in foods), 1),
        fat_g=round(sum(f.fat_g for f in foods), 1),
        water_ml=round(sum(w.volume_ml for w in waters), 1),
        food_count=len(foods),
        exercise_count=len(exercises),
    )


def build_weight_trend(entries: Sequence[LoggedWeight]) -> WeightTrend:
    """Build a weight trend from entries, ordering them oldest → newest.

    Robust to input order: it sorts by ``logged_at`` so ``start``/``latest`` are
    the true endpoints regardless of how the repository returned the rows.
    """
    ordered = sorted(entries, key=lambda e: (e.logged_at, e.id))
    if not ordered:
        return WeightTrend(entries=[], start_kg=None, latest_kg=None, change_kg=None)

    start = ordered[0].weight_kg
    latest = ordered[-1].weight_kg
    return WeightTrend(
        entries=ordered,
        start_kg=start,
        latest_kg=latest,
        change_kg=round(latest - start, 1),
    )
