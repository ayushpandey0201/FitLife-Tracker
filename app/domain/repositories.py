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
    """Persistence contract for :class:`~app.domain.models.UserProfile` records."""

    def add(self, profile: UserProfile) -> StoredProfile:
        """Persist a new profile and return it with its assigned identity."""
        ...

    def get(self, profile_id: int) -> StoredProfile | None:
        """Return the stored profile with ``profile_id``, or ``None`` if absent."""
        ...

    def list_all(self) -> list[StoredProfile]:
        """Return every stored profile, ordered by identity (insertion order)."""
        ...
