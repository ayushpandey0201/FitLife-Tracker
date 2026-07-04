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
