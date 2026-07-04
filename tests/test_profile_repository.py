"""Tests for the SQLAlchemy profile repository (against in-memory SQLite)."""

from __future__ import annotations

from app.db.models import User
from app.domain.enums import ActivityLevel, DietPreference, Goal, Sex
from app.domain.models import StoredProfile
from app.domain.repositories import ProfileRepository
from app.repositories.profile_repository import SqlAlchemyProfileRepository
from sqlalchemy.orm import Session

from tests.test_nutrition import make_profile


def _user(session: Session, email: str = "owner@example.com") -> User:
    user = User(email=email, hashed_password="x", role="user")
    session.add(user)
    session.flush()
    return user


def _repo(session: Session) -> SqlAlchemyProfileRepository:
    return SqlAlchemyProfileRepository(session)


def test_add_assigns_identity_and_roundtrips(db_session: Session) -> None:
    repo = _repo(db_session)
    user = _user(db_session)
    profile = make_profile(name="Ayush", weight_kg=82, target_weight_kg=75)

    stored = repo.add(user.id, profile)

    assert isinstance(stored, StoredProfile)
    assert stored.id >= 1
    assert stored.profile == profile
    assert repo.get_for_user(user.id, stored.id) == stored


def test_get_missing_returns_none(db_session: Session) -> None:
    user = _user(db_session)
    assert _repo(db_session).get_for_user(user.id, 999) is None


def test_reads_are_scoped_to_owner(db_session: Session) -> None:
    """A profile is invisible to a different user."""
    repo = _repo(db_session)
    alice = _user(db_session, "alice@example.com")
    bob = _user(db_session, "bob@example.com")
    stored = repo.add(alice.id, make_profile(name="Alice"))

    assert repo.get_for_user(bob.id, stored.id) is None
    assert repo.list_for_user(bob.id) == []


def test_get_current_returns_latest(db_session: Session) -> None:
    repo = _repo(db_session)
    user = _user(db_session)
    repo.add(user.id, make_profile(name="old", weight_kg=90))
    latest = repo.add(user.id, make_profile(name="new", weight_kg=85))
    assert repo.get_current(user.id) == latest


def test_list_for_user_is_newest_first(db_session: Session) -> None:
    repo = _repo(db_session)
    user = _user(db_session)
    ids = [repo.add(user.id, make_profile(name=f"u{i}")).id for i in range(3)]
    assert [s.id for s in repo.list_for_user(user.id)] == sorted(ids, reverse=True)


def test_enums_persist_and_reparse(db_session: Session) -> None:
    repo = _repo(db_session)
    user = _user(db_session)
    profile = make_profile(
        sex=Sex.FEMALE,
        activity_level=ActivityLevel.VERY_ACTIVE,
        diet_preference=DietPreference.VEGETARIAN,
    )
    fetched = repo.get_for_user(user.id, repo.add(user.id, profile).id)
    assert fetched is not None
    assert fetched.profile.sex is Sex.FEMALE
    assert fetched.profile.activity_level is ActivityLevel.VERY_ACTIVE
    assert fetched.profile.diet_preference is DietPreference.VEGETARIAN


def test_computed_goal_survives_roundtrip(db_session: Session) -> None:
    repo = _repo(db_session)
    user = _user(db_session)
    stored = repo.add(user.id, make_profile(weight_kg=90, target_weight_kg=75))
    fetched = repo.get_for_user(user.id, stored.id)
    assert fetched is not None
    assert fetched.profile.goal is Goal.LOSE


def test_adapter_satisfies_port(db_session: Session) -> None:
    assert isinstance(_repo(db_session), ProfileRepository)
