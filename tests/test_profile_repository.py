"""Tests for the SQLAlchemy profile repository (against in-memory SQLite)."""

from __future__ import annotations

from app.domain.enums import ActivityLevel, DietPreference, Goal, Sex
from app.domain.models import StoredProfile
from app.domain.repositories import ProfileRepository
from app.repositories.profile_repository import SqlAlchemyProfileRepository
from sqlalchemy.orm import Session

from tests.test_nutrition import make_profile


def _repo(session: Session) -> SqlAlchemyProfileRepository:
    return SqlAlchemyProfileRepository(session)


def test_add_assigns_identity_and_roundtrips(db_session: Session) -> None:
    repo = _repo(db_session)
    profile = make_profile(name="Ayush", weight_kg=82, target_weight_kg=75)

    stored = repo.add(profile)

    assert isinstance(stored, StoredProfile)
    assert stored.id >= 1
    assert stored.profile == profile
    # Fetched back by id, it is identical.
    assert repo.get(stored.id) == stored


def test_get_missing_returns_none(db_session: Session) -> None:
    assert _repo(db_session).get(999) is None


def test_list_all_is_ordered_by_id(db_session: Session) -> None:
    repo = _repo(db_session)
    ids = [repo.add(make_profile(name=f"user-{i}")).id for i in range(3)]
    listed = repo.list_all()
    assert [s.id for s in listed] == sorted(ids)


def test_enums_persist_and_reparse(db_session: Session) -> None:
    """Enum columns stored as strings must re-hydrate to the right enums."""
    repo = _repo(db_session)
    profile = make_profile(
        sex=Sex.FEMALE,
        activity_level=ActivityLevel.VERY_ACTIVE,
        diet_preference=DietPreference.VEGETARIAN,
    )
    fetched = repo.get(repo.add(profile).id)
    assert fetched is not None
    assert fetched.profile.sex is Sex.FEMALE
    assert fetched.profile.activity_level is ActivityLevel.VERY_ACTIVE
    assert fetched.profile.diet_preference is DietPreference.VEGETARIAN


def test_computed_goal_survives_roundtrip(db_session: Session) -> None:
    """The derived ``goal`` is recomputed from persisted weights, not stored."""
    repo = _repo(db_session)
    stored = repo.add(make_profile(weight_kg=90, target_weight_kg=75))
    fetched = repo.get(stored.id)
    assert fetched is not None
    assert fetched.profile.goal is Goal.LOSE


def test_adapter_satisfies_port(db_session: Session) -> None:
    """The concrete adapter structurally satisfies the domain port."""
    assert isinstance(_repo(db_session), ProfileRepository)
