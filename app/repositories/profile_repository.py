"""SQLAlchemy adapter for :class:`~app.domain.repositories.ProfileRepository`.

Translates between the persistence :class:`~app.db.models.UserProfileRecord` and
the pure domain :class:`~app.domain.models.UserProfile` / ``StoredProfile``. The
session is injected, so the same adapter serves the CLI (via ``session_scope``)
and, later, a per-request API session.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UserProfileRecord
from app.domain.enums import ActivityLevel, DietPreference, Sex
from app.domain.models import StoredProfile, UserProfile
from app.logging_config import get_logger

logger = get_logger(__name__)


def _to_domain(record: UserProfileRecord) -> StoredProfile:
    """Map an ORM row to the domain read model, re-validating enum values."""
    profile = UserProfile(
        name=record.name,
        age=record.age,
        height_cm=record.height_cm,
        weight_kg=record.weight_kg,
        target_weight_kg=record.target_weight_kg,
        sex=Sex(record.sex),
        activity_level=ActivityLevel(record.activity_level),
        diet_preference=DietPreference(record.diet_preference),
        weeks_to_target=record.weeks_to_target,
    )
    return StoredProfile(id=record.id, profile=profile)


def _to_record(profile: UserProfile) -> UserProfileRecord:
    """Map a domain profile to a new ORM row (enums stored as their values)."""
    return UserProfileRecord(
        name=profile.name,
        age=profile.age,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        target_weight_kg=profile.target_weight_kg,
        sex=profile.sex.value,
        activity_level=profile.activity_level.value,
        diet_preference=profile.diet_preference.value,
        weeks_to_target=profile.weeks_to_target,
    )


class SqlAlchemyProfileRepository:
    """Concrete :class:`ProfileRepository` backed by a SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, profile: UserProfile) -> StoredProfile:
        record = _to_record(profile)
        self._session.add(record)
        # Flush (not commit) so the id is assigned while leaving the enclosing
        # transaction — owned by the caller/session_scope — in control.
        self._session.flush()
        logger.info("profile_persisted id=%d", record.id)
        return _to_domain(record)

    def get(self, profile_id: int) -> StoredProfile | None:
        record = self._session.get(UserProfileRecord, profile_id)
        return _to_domain(record) if record is not None else None

    def list_all(self) -> list[StoredProfile]:
        stmt = select(UserProfileRecord).order_by(UserProfileRecord.id)
        return [_to_domain(r) for r in self._session.scalars(stmt)]
