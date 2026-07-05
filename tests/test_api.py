"""End-to-end API tests over the FastAPI app.

Exercises the HTTP layer (routing, auth dependency, error mapping) against a real
service + repository stack backed by a shared in-memory SQLite database. The two
injected seams — the DB session and settings — are overridden so no external
Postgres is needed and a deterministic JWT secret is used.
"""

from __future__ import annotations

from collections.abc import Iterator

# Register ORM tables on Base.metadata before create_all.
import app.db.models  # noqa: F401
import pytest
from app.api.app import create_app
from app.api.dependencies.auth import provide_settings
from app.api.dependencies.db import get_db
from app.config import AppEnv, Settings
from app.db.base import Base
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

_PROFILE_PAYLOAD = {
    "name": "Test",
    "age": 30,
    "height_cm": 175,
    "weight_kg": 80,
    "target_weight_kg": 75,
    "sex": "male",
    "activity_level": "moderate",
    "weeks_to_target": 10,
}


def _settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env=AppEnv.TESTING,
        jwt_secret_key="api-test-secret-at-least-32-bytes-long!!",
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient wired to a fresh, shared in-memory SQLite database."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def _override_db() -> Iterator[Session]:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app(_settings())
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[provide_settings] = _settings
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _register_and_login(client: TestClient, email: str = "a@example.com") -> str:
    """Register an account and return an ``Authorization`` bearer header value."""
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return f"Bearer {r.json()['access_token']}"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": token}


# --- meta / auth -----------------------------------------------------------
def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_register_conflict_returns_409(client: TestClient) -> None:
    body = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/auth/register", json=body).status_code == 201
    r = client.post("/auth/register", json=body)
    assert r.status_code == 409


def test_login_bad_credentials_returns_401(client: TestClient) -> None:
    _register_and_login(client)
    r = client.post("/auth/login", json={"email": "a@example.com", "password": "nope-wrong"})
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_me_requires_auth(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    token = _register_and_login(client)
    r = client.get("/auth/me", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"


def test_refresh_rotates_and_revokes_old(client: TestClient) -> None:
    client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    login = client.post(
        "/auth/login", json={"email": "a@example.com", "password": "password123"}
    ).json()
    refresh_token = login["refresh_token"]

    r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    # The rotated (old) token can no longer be used.
    assert client.post("/auth/refresh", json={"refresh_token": refresh_token}).status_code == 401


def test_logout_is_idempotent_204(client: TestClient) -> None:
    _register_and_login(client)
    tokens = client.post(
        "/auth/login", json={"email": "a@example.com", "password": "password123"}
    ).json()
    r = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 204
    # Revoked token cannot refresh.
    assert (
        client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code
        == 401
    )


# --- profiles --------------------------------------------------------------
def test_profile_crud_flow(client: TestClient) -> None:
    token = _register_and_login(client)
    # No profile yet.
    assert client.get("/profiles/current", headers=_auth(token)).status_code == 404

    created = client.post("/profiles", headers=_auth(token), json=_PROFILE_PAYLOAD)
    assert created.status_code == 201, created.text
    assert created.json()["goal"] == "lose"

    current = client.get("/profiles/current", headers=_auth(token))
    assert current.status_code == 200
    assert current.json()["profile"]["name"] == "Test"

    history = client.get("/profiles", headers=_auth(token))
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_profile_validation_returns_422(client: TestClient) -> None:
    token = _register_and_login(client)
    bad = {**_PROFILE_PAYLOAD, "age": 5}  # below ge=13
    assert client.post("/profiles", headers=_auth(token), json=bad).status_code == 422


# --- plans -----------------------------------------------------------------
def test_plan_requires_profile_404(client: TestClient) -> None:
    token = _register_and_login(client)
    assert client.post("/plans", headers=_auth(token)).status_code == 404


def test_plan_generate_and_fetch_flow(client: TestClient) -> None:
    token = _register_and_login(client)
    client.post("/profiles", headers=_auth(token), json=_PROFILE_PAYLOAD)

    generated = client.post("/plans", headers=_auth(token))
    assert generated.status_code == 201, generated.text
    plan_id = generated.json()["id"]

    fetched = client.get(f"/plans/{plan_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["nutrition_plan"]["calorie_target_kcal"] > 0

    history = client.get("/plans", headers=_auth(token))
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_plan_isolated_per_user(client: TestClient) -> None:
    token_a = _register_and_login(client, email="a@example.com")
    client.post("/profiles", headers=_auth(token_a), json=_PROFILE_PAYLOAD)
    plan_id = client.post("/plans", headers=_auth(token_a)).json()["id"]

    token_b = _register_and_login(client, email="b@example.com")
    # B cannot see A's plan — 404, not 403 (existence is not leaked).
    assert client.get(f"/plans/{plan_id}", headers=_auth(token_b)).status_code == 404


# --- tracking logs (Phase 5) -----------------------------------------------
def _user_with_profile(client: TestClient, email: str = "a@example.com") -> str:
    """Register/login and attach a profile; return the auth header value."""
    token = _register_and_login(client, email=email)
    r = client.post("/profiles", headers=_auth(token), json=_PROFILE_PAYLOAD)
    assert r.status_code == 201, r.text
    return token


def test_logs_require_auth(client: TestClient) -> None:
    assert client.get("/logs/weight").status_code == 401
    assert client.post("/logs/water", json={"volume_ml": 500}).status_code == 401


def test_weight_log_crud_flow(client: TestClient) -> None:
    token = _user_with_profile(client)
    created = client.post("/logs/weight", headers=_auth(token), json={"weight_kg": 79.5})
    assert created.status_code == 201, created.text
    log_id = created.json()["id"]

    listing = client.get("/logs/weight", headers=_auth(token))
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    assert client.delete(f"/logs/weight/{log_id}", headers=_auth(token)).status_code == 204
    # Deleting again is a 404 (gone / not the caller's).
    assert client.delete(f"/logs/weight/{log_id}", headers=_auth(token)).status_code == 404


def test_water_log_validation_422(client: TestClient) -> None:
    token = _user_with_profile(client)
    r = client.post("/logs/water", headers=_auth(token), json={"volume_ml": 0})  # gt=0
    assert r.status_code == 422


def test_exercise_log_derives_calories(client: TestClient) -> None:
    token = _user_with_profile(client)  # profile weight is 80 kg
    r = client.post(
        "/logs/exercise",
        headers=_auth(token),
        json={"exercise": "Running", "duration_min": 30},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["met"] == 9.8
    assert body["calories_burned_kcal"] == 392.0


def test_exercise_log_requires_profile_404(client: TestClient) -> None:
    token = _register_and_login(client)  # no profile created
    r = client.post(
        "/logs/exercise",
        headers=_auth(token),
        json={"exercise": "Running", "duration_min": 30},
    )
    assert r.status_code == 404


def test_exercise_log_unknown_name_404(client: TestClient) -> None:
    token = _user_with_profile(client)
    r = client.post(
        "/logs/exercise",
        headers=_auth(token),
        json={"exercise": "Quidditch", "duration_min": 30},
    )
    assert r.status_code == 404


def test_progress_daily_summary(client: TestClient) -> None:
    token = _user_with_profile(client)
    day = "2026-07-04"
    at = f"{day}T12:00:00Z"
    client.post(
        "/logs/food",
        headers=_auth(token),
        json={"name": "Oats", "calories_kcal": 300, "protein_g": 10, "logged_at": at},
    )
    client.post("/logs/water", headers=_auth(token), json={"volume_ml": 600, "logged_at": at})
    client.post(
        "/logs/exercise",
        headers=_auth(token),
        json={"exercise": "Running", "duration_min": 30, "logged_at": at},
    )

    r = client.get("/progress/daily", headers=_auth(token), params={"on": day})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["calories_consumed_kcal"] == 300.0
    assert body["calories_burned_kcal"] == 392.0
    assert body["net_calories_kcal"] == -92.0
    assert body["water_ml"] == 600.0


def test_progress_weight_trend(client: TestClient) -> None:
    token = _user_with_profile(client)
    for day, kg in [("2026-07-01", 82.0), ("2026-07-05", 79.0)]:
        client.post(
            "/logs/weight",
            headers=_auth(token),
            json={"weight_kg": kg, "logged_at": f"{day}T09:00:00Z"},
        )
    r = client.get("/progress/weight", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["start_kg"] == 82.0
    assert body["latest_kg"] == 79.0
    assert body["change_kg"] == -3.0


def test_logs_isolated_per_user(client: TestClient) -> None:
    token_a = _user_with_profile(client, email="a@example.com")
    log_id = client.post("/logs/weight", headers=_auth(token_a), json={"weight_kg": 80}).json()[
        "id"
    ]

    token_b = _user_with_profile(client, email="b@example.com")
    assert client.get("/logs/weight", headers=_auth(token_b)).json() == []
    # B cannot delete A's log.
    assert client.delete(f"/logs/weight/{log_id}", headers=_auth(token_b)).status_code == 404
