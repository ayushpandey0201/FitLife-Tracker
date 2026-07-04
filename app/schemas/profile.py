"""Profile request/response schemas.

The **request** body reuses the domain :class:`~app.domain.models.UserProfile`
directly — its validation (age/height/weight bounds, cross-field goal) is exactly
what the API needs, and reusing it keeps a single source of truth. The response
adds the persistence id and derived goal.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.enums import Goal
from app.domain.models import StoredProfile, UserProfile

# The create payload IS the domain profile (no duplication).
ProfileCreate = UserProfile


class ProfileOut(BaseModel):
    """A persisted profile with its id and derived goal."""

    id: int
    profile: UserProfile
    goal: Goal

    @classmethod
    def from_stored(cls, stored: StoredProfile) -> ProfileOut:
        """Build the response from a repository :class:`StoredProfile`."""
        return cls(id=stored.id, profile=stored.profile, goal=stored.profile.goal)
