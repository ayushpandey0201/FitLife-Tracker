"""Plan endpoints: generate a nutrition plan from the current profile, read history.

Generating a plan uses the user's *current* profile (404 if they have none), runs
the pure domain engine, and persists the result as a durable, user-scoped record.
Reads are user-scoped: a plan id that isn't the caller's returns 404, not 403, so
plan existence isn't leaked across accounts.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.services import PlanServiceDep, ProfileServiceDep
from app.schemas.plan import PlanOut, PlanSummary

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post(
    "",
    response_model=PlanOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a plan from the current profile",
)
def generate_plan(
    current_user: CurrentUser,
    profiles: ProfileServiceDep,
    plans: PlanServiceDep,
) -> PlanOut:
    """Build and persist a plan from the user's current profile (404 if none)."""
    stored_profile = profiles.get_current(current_user.id)
    return plans.generate(current_user.id, stored_profile)


@router.get(
    "",
    response_model=list[PlanSummary],
    summary="Plan history (newest first)",
)
def list_plans(current_user: CurrentUser, plans: PlanServiceDep) -> list[PlanSummary]:
    """Return lightweight summaries of the user's plans, newest first."""
    return plans.list_history(current_user.id)


@router.get("/{plan_id}", response_model=PlanOut, summary="Fetch one plan")
def get_plan(
    plan_id: int,
    current_user: CurrentUser,
    plans: PlanServiceDep,
) -> PlanOut:
    """Return one of the user's plans in full, or 404 if it isn't theirs."""
    return plans.get(current_user.id, plan_id)
