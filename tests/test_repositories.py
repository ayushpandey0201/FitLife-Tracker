"""Tests for the user, refresh-token, and plan repositories (in-memory SQLite)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db.models import User
from app.repositories.plan_repository import SqlAlchemyPlanRepository
from app.repositories.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from app.repositories.user_repository import SqlAlchemyUserRepository
from sqlalchemy.orm import Session


def _make_user(session: Session, email: str = "u@example.com") -> User:
    return SqlAlchemyUserRepository(session).add(email=email, hashed_password="hash")


# --- users -----------------------------------------------------------------
def test_user_add_and_lookup(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    user = repo.add(email="a@example.com", hashed_password="h")
    assert user.id >= 1
    assert user.role == "user"
    assert user.is_active is True
    assert repo.get_by_email("a@example.com") is user
    assert repo.get_by_id(user.id) is user
    assert repo.get_by_email("missing@example.com") is None


# --- refresh tokens --------------------------------------------------------
def test_refresh_token_add_lookup_revoke(db_session: Session) -> None:
    user = _make_user(db_session)
    repo = SqlAlchemyRefreshTokenRepository(db_session)
    expires = datetime.now(UTC) + timedelta(days=7)

    token = repo.add(user_id=user.id, jti="jti-1", token_hash="h1", expires_at=expires)
    assert token.revoked is False
    assert repo.get_by_jti("jti-1") is token

    repo.revoke(token)
    assert repo.get_by_jti("jti-1").revoked is True
    assert repo.get_by_jti("nope") is None


# --- plans -----------------------------------------------------------------
def test_plan_add_scoped_reads(db_session: Session) -> None:
    alice = _make_user(db_session, "alice@example.com")
    bob = _make_user(db_session, "bob@example.com")
    repo = SqlAlchemyPlanRepository(db_session)

    plan = repo.add(
        user_id=alice.id,
        profile_id=None,
        goal="lose",
        diet_preference="non_vegetarian",
        calorie_target_kcal=2000.0,
        bmi=24.5,
        nutrition_plan={"calorie_target_kcal": 2000.0},
        meal_plan={"meals": []},
    )
    assert plan.id >= 1
    # Owner can read; other user cannot.
    assert repo.get_for_user(alice.id, plan.id) is plan
    assert repo.get_for_user(bob.id, plan.id) is None
    assert [p.id for p in repo.list_for_user(alice.id)] == [plan.id]
    assert repo.list_for_user(bob.id) == []


def test_plan_list_is_newest_first(db_session: Session) -> None:
    user = _make_user(db_session)
    repo = SqlAlchemyPlanRepository(db_session)
    ids = [
        repo.add(
            user_id=user.id,
            profile_id=None,
            goal="maintain",
            diet_preference="vegetarian",
            calorie_target_kcal=2100.0,
            bmi=22.0,
            nutrition_plan={},
            meal_plan={},
        ).id
        for _ in range(3)
    ]
    assert [p.id for p in repo.list_for_user(user.id)] == sorted(ids, reverse=True)
