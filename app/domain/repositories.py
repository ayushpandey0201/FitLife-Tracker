"""Repository ports (interfaces) — the persistence seam.

These are the *ports* of the hexagonal/clean architecture: abstract contracts
the domain and application layers depend on, with concrete adapters (SQLAlchemy,
in-memory, ...) supplied from the outside. Declaring them here — with no import
of any storage technology — keeps the domain free of infrastructure while making
persistence swappable and trivially fakeable in tests.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.models import StoredProfile, UserProfile


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
