"""Tracking-log endpoints: record, list, and delete weight/water/food/exercise.

Four parallel resources under ``/logs``. Each is user-scoped via
:data:`CurrentUser`, validates its body against the domain input schema, and
calls one :class:`~app.services.tracking_service.TrackingService` use case.
Deleting a log that isn't the caller's returns 404 (existence isn't leaked);
logging exercise requires a current profile and a catalogue match (both → 404).
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.services import TrackingServiceDep
from app.schemas.tracking import (
    ExerciseLogCreate,
    ExerciseLogOut,
    FoodLogCreate,
    FoodLogOut,
    WaterLogCreate,
    WaterLogOut,
    WeightLogCreate,
    WeightLogOut,
)

router = APIRouter(prefix="/logs", tags=["logs"])


# -- weight -----------------------------------------------------------------
@router.post(
    "/weight",
    response_model=WeightLogOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record a weight measurement",
)
def log_weight(
    payload: WeightLogCreate, user: CurrentUser, tracking: TrackingServiceDep
) -> WeightLogOut:
    """Record a body-weight entry (defaults to now if no timestamp is given)."""
    return tracking.log_weight(user.id, payload)


@router.get("/weight", response_model=list[WeightLogOut], summary="Weight history")
def list_weights(user: CurrentUser, tracking: TrackingServiceDep) -> list[WeightLogOut]:
    """List the user's weight entries, newest first."""
    return tracking.list_weights(user.id)


@router.delete(
    "/weight/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a weight entry",
)
def delete_weight(log_id: int, user: CurrentUser, tracking: TrackingServiceDep) -> None:
    """Delete one of the user's weight entries (404 if it isn't theirs)."""
    tracking.delete_weight(user.id, log_id)


# -- water ------------------------------------------------------------------
@router.post(
    "/water",
    response_model=WaterLogOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record water intake",
)
def log_water(
    payload: WaterLogCreate, user: CurrentUser, tracking: TrackingServiceDep
) -> WaterLogOut:
    """Record a water-intake entry."""
    return tracking.log_water(user.id, payload)


@router.get("/water", response_model=list[WaterLogOut], summary="Water history")
def list_waters(user: CurrentUser, tracking: TrackingServiceDep) -> list[WaterLogOut]:
    """List the user's water entries, newest first."""
    return tracking.list_waters(user.id)


@router.delete(
    "/water/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a water entry",
)
def delete_water(log_id: int, user: CurrentUser, tracking: TrackingServiceDep) -> None:
    """Delete one of the user's water entries (404 if it isn't theirs)."""
    tracking.delete_water(user.id, log_id)


# -- food -------------------------------------------------------------------
@router.post(
    "/food",
    response_model=FoodLogOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record a food/meal",
)
def log_food(
    payload: FoodLogCreate, user: CurrentUser, tracking: TrackingServiceDep
) -> FoodLogOut:
    """Record a food entry with its nutrition as consumed."""
    return tracking.log_food(user.id, payload)


@router.get("/food", response_model=list[FoodLogOut], summary="Food history")
def list_foods(user: CurrentUser, tracking: TrackingServiceDep) -> list[FoodLogOut]:
    """List the user's food entries, newest first."""
    return tracking.list_foods(user.id)


@router.delete(
    "/food/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a food entry",
)
def delete_food(log_id: int, user: CurrentUser, tracking: TrackingServiceDep) -> None:
    """Delete one of the user's food entries (404 if it isn't theirs)."""
    tracking.delete_food(user.id, log_id)


# -- exercise ---------------------------------------------------------------
@router.post(
    "/exercise",
    response_model=ExerciseLogOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record an exercise session",
)
def log_exercise(
    payload: ExerciseLogCreate, user: CurrentUser, tracking: TrackingServiceDep
) -> ExerciseLogOut:
    """Record an exercise session; energy burned is derived server-side.

    Requires a current profile (for body weight) and a catalogue exercise name.
    """
    return tracking.log_exercise(user.id, payload)


@router.get(
    "/exercise", response_model=list[ExerciseLogOut], summary="Exercise history"
)
def list_exercises(
    user: CurrentUser, tracking: TrackingServiceDep
) -> list[ExerciseLogOut]:
    """List the user's exercise entries, newest first."""
    return tracking.list_exercises(user.id)


@router.delete(
    "/exercise/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an exercise entry",
)
def delete_exercise(
    log_id: int, user: CurrentUser, tracking: TrackingServiceDep
) -> None:
    """Delete one of the user's exercise entries (404 if it isn't theirs)."""
    tracking.delete_exercise(user.id, log_id)
