"""Profile endpoints: create a profile version, read the current one, list history.

All routes are user-scoped via the authenticated :data:`CurrentUser`; a caller
can only ever see or create their own profiles. The create payload is the domain
:class:`~app.domain.models.UserProfile` itself, so its validation is enforced by
FastAPI (invalid input → 422) with no duplication.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.services import ProfileServiceDep
from app.schemas.profile import ProfileCreate, ProfileOut

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post(
    "",
    response_model=ProfileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new profile version",
)
def create_profile(
    payload: ProfileCreate,
    current_user: CurrentUser,
    profiles: ProfileServiceDep,
) -> ProfileOut:
    """Persist a new profile for the current user; the newest becomes current."""
    stored = profiles.create(current_user.id, payload)
    return ProfileOut.from_stored(stored)


@router.get("/current", response_model=ProfileOut, summary="Current profile")
def get_current_profile(
    current_user: CurrentUser,
    profiles: ProfileServiceDep,
) -> ProfileOut:
    """Return the user's latest profile, or 404 if none has been created."""
    stored = profiles.get_current(current_user.id)
    return ProfileOut.from_stored(stored)


@router.get(
    "",
    response_model=list[ProfileOut],
    summary="Profile history (newest first)",
)
def list_profiles(
    current_user: CurrentUser,
    profiles: ProfileServiceDep,
) -> list[ProfileOut]:
    """Return every profile the user has created, newest first."""
    return [ProfileOut.from_stored(s) for s in profiles.list_history(current_user.id)]
