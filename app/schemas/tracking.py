"""Tracking request/response schemas.

Like :mod:`app.schemas.profile`, the HTTP contract reuses the domain value
objects directly rather than duplicating them: the ``*Entry`` inputs already
carry exactly the validation the API needs, and the ``Logged*`` / analytics
models are the responses. Aliasing them here gives routers a single, intent-
revealing import point (``WeightLogCreate`` reads better in a route than
``WeightEntry``) without a second source of truth.
"""

from __future__ import annotations

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
)

# Request bodies (the domain inputs).
WeightLogCreate = WeightEntry
WaterLogCreate = WaterEntry
FoodLogCreate = FoodEntry
ExerciseLogCreate = ExerciseEntry

# Responses.
WeightLogOut = LoggedWeight
WaterLogOut = LoggedWater
FoodLogOut = LoggedFood
ExerciseLogOut = LoggedExercise
DailySummaryOut = DailySummary
WeightTrendOut = WeightTrend

__all__ = [
    "DailySummaryOut",
    "ExerciseLogCreate",
    "ExerciseLogOut",
    "FoodLogCreate",
    "FoodLogOut",
    "WaterLogCreate",
    "WaterLogOut",
    "WeightLogCreate",
    "WeightLogOut",
    "WeightTrendOut",
]
