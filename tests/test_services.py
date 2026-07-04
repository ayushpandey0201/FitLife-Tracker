"""Tests for the application services (auth, profile, plan)."""

from __future__ import annotations

import pytest
from app.config import AppEnv, Settings
from app.services.auth_service import AuthService
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    PlanNotFoundError,
    ProfileNotFoundError,
)
from app.services.plan_service import PlanService
from app.services.profile_service import ProfileService
from sqlalchemy.orm import Session

from tests.test_nutrition import make_profile


def _settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env=AppEnv.TESTING,
        jwt_secret_key="service-test-secret-at-least-32-bytes!!",
    )


def _auth(session: Session) -> AuthService:
    return AuthService(session, _settings())


# --- auth ------------------------------------------------------------------
def test_register_and_login_flow(db_session: Session) -> None:
    auth = _auth(db_session)
    user = auth.register(email="a@example.com", password="password123")
    assert user.id >= 1

    pair = auth.login(email="a@example.com", password="password123")
    assert pair.access_token and pair.refresh_token
    assert pair.token_type == "bearer"
    assert pair.expires_in > 0


def test_duplicate_email_rejected(db_session: Session) -> None:
    auth = _auth(db_session)
    auth.register(email="dup@example.com", password="password123")
    with pytest.raises(EmailAlreadyExistsError):
        auth.register(email="dup@example.com", password="password123")


def test_login_wrong_password_rejected(db_session: Session) -> None:
    auth = _auth(db_session)
    auth.register(email="a@example.com", password="password123")
    with pytest.raises(InvalidCredentialsError):
        auth.login(email="a@example.com", password="wrong-password")


def test_refresh_rotates_and_old_token_is_revoked(db_session: Session) -> None:
    auth = _auth(db_session)
    auth.register(email="a@example.com", password="password123")
    pair = auth.login(email="a@example.com", password="password123")

    rotated = auth.refresh(pair.refresh_token)
    assert rotated.refresh_token != pair.refresh_token
    # The old refresh token no longer works (rotation revoked it).
    with pytest.raises(InvalidTokenError):
        auth.refresh(pair.refresh_token)


def test_logout_revokes_refresh_token(db_session: Session) -> None:
    auth = _auth(db_session)
    auth.register(email="a@example.com", password="password123")
    pair = auth.login(email="a@example.com", password="password123")

    auth.logout(pair.refresh_token)
    with pytest.raises(InvalidTokenError):
        auth.refresh(pair.refresh_token)


def test_access_token_is_not_accepted_as_refresh(db_session: Session) -> None:
    auth = _auth(db_session)
    auth.register(email="a@example.com", password="password123")
    pair = auth.login(email="a@example.com", password="password123")
    with pytest.raises(InvalidTokenError):
        auth.refresh(pair.access_token)


# --- profile ---------------------------------------------------------------
def test_profile_service_current_and_history(db_session: Session) -> None:
    user = _auth(db_session).register(email="p@example.com", password="password123")
    svc = ProfileService(db_session)

    with pytest.raises(ProfileNotFoundError):
        svc.get_current(user.id)

    svc.create(user.id, make_profile(name="v1", weight_kg=90))
    latest = svc.create(user.id, make_profile(name="v2", weight_kg=85))
    assert svc.get_current(user.id) == latest
    assert len(svc.list_history(user.id)) == 2


# --- plan ------------------------------------------------------------------
def test_plan_service_generates_persists_and_scopes(db_session: Session) -> None:
    auth = _auth(db_session)
    alice = auth.register(email="alice@example.com", password="password123")
    bob = auth.register(email="bob@example.com", password="password123")
    profiles = ProfileService(db_session)
    plans = PlanService(db_session)

    stored = profiles.create(alice.id, make_profile(weight_kg=82, target_weight_kg=75))
    out = plans.generate(alice.id, stored)

    assert out.id >= 1
    assert out.calorie_target_kcal > 0
    assert len(out.meal_plan.meals) == 3
    # Persisted and retrievable by the owner.
    assert plans.get(alice.id, out.id).id == out.id
    assert len(plans.list_history(alice.id)) == 1
    # Bob cannot see Alice's plan.
    with pytest.raises(PlanNotFoundError):
        plans.get(bob.id, out.id)
