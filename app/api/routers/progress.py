"""Progress/analytics endpoints: daily summary and weight trend.

Read-only views computed from the tracking logs. Dates are interpreted in **UTC**
(matching how logs are bucketed); ``/daily`` defaults to today when no date is
given, and ``/weight`` accepts an optional inclusive ``[start, end]`` range.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.services import TrackingServiceDep
from app.schemas.tracking import DailySummaryOut, WeightTrendOut

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/daily", response_model=DailySummaryOut, summary="Daily tracking summary")
def daily_summary(
    user: CurrentUser,
    tracking: TrackingServiceDep,
    on: Annotated[
        date | None, Query(description="UTC date to summarise; defaults to today")
    ] = None,
) -> DailySummaryOut:
    """Summarise the user's food/exercise/water logs for a single UTC day."""
    day = on or datetime.now(UTC).date()
    return tracking.daily_summary(user.id, day)


@router.get("/weight", response_model=WeightTrendOut, summary="Weight trend")
def weight_trend(
    user: CurrentUser,
    tracking: TrackingServiceDep,
    start: Annotated[date | None, Query(description="Inclusive start date")] = None,
    end: Annotated[date | None, Query(description="Inclusive end date")] = None,
) -> WeightTrendOut:
    """Return the user's weight series and net change over an optional range."""
    return tracking.weight_trend(user.id, start=start, end=end)
