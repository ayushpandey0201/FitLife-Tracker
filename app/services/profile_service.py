"""Profile service: create and read a user's fitness profiles.

Thin orchestration over the user-scoped profile repository. Profiles are kept as
versioned history (a user may create several over time); the newest is current.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.models import StoredProfile, UserProfile
from app.logging_config import get_logger
from app.repositories.profile_repository import SqlAlchemyProfileRepository
from app.services.exceptions import ProfileNotFoundError

logger = get_logger(__name__)


class ProfileService:
    """Use cases for user fitness profiles."""

    def __init__(self, session: Session) -> None:
        self._profiles = SqlAlchemyProfileRepository(session)

    def create(self, user_id: int, profile: UserProfile) -> StoredProfile:
        """Persist a new profile version for the user."""
        stored = self._profiles.add(user_id, profile)
        logger.info("profile_created id=%d user_id=%d", stored.id, user_id)
        return stored

    def get_current(self, user_id: int) -> StoredProfile:
        """Return the user's current (latest) profile, or raise if none exist."""
        current = self._profiles.get_current(user_id)
        if current is None:
            raise ProfileNotFoundError("no profile has been created yet")
        return current

    def list_history(self, user_id: int) -> list[StoredProfile]:
        """Return all of the user's profiles, newest first."""
        return self._profiles.list_for_user(user_id)
