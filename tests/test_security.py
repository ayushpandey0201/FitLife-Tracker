"""Unit tests for password hashing and JWT tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from app.config import AppEnv, Settings
from app.security.password import hash_password, verify_password
from app.security.tokens import (
    TokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "jwt_secret_key": "test-secret-key-at-least-32-bytes-long!!",
        "app_env": AppEnv.TESTING,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


# --- passwords -------------------------------------------------------------
def test_hash_is_salted_and_verifiable() -> None:
    h1 = hash_password("s3cret")
    h2 = hash_password("s3cret")
    assert h1 != h2  # unique salts
    assert h1.startswith("$argon2")
    assert verify_password(h1, "s3cret")
    assert verify_password(h2, "s3cret")


def test_verify_rejects_wrong_password_and_garbage() -> None:
    h = hash_password("correct-horse")
    assert not verify_password(h, "wrong")
    assert not verify_password("not-a-hash", "correct-horse")


# --- tokens ----------------------------------------------------------------
def test_access_token_roundtrip() -> None:
    s = _settings()
    issued = create_access_token(s, subject="42", role="user")
    decoded = decode_token(s, issued.token, expected_type=TokenType.ACCESS)
    assert decoded.subject == "42"
    assert decoded.role == "user"
    assert decoded.token_type is TokenType.ACCESS
    assert decoded.jti == issued.jti


def test_token_type_is_enforced() -> None:
    s = _settings()
    refresh = create_refresh_token(s, subject="1", role="user")
    # A refresh token must not be accepted where an access token is expected.
    with pytest.raises(TokenError):
        decode_token(s, refresh.token, expected_type=TokenType.ACCESS)


def test_expired_token_is_rejected() -> None:
    s = _settings()
    expired = jwt.encode(
        {
            "sub": "1",
            "role": "user",
            "type": "access",
            "jti": "x",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        s.jwt_secret_key,
        algorithm=s.jwt_algorithm,
    )
    with pytest.raises(TokenError):
        decode_token(s, expired, expected_type=TokenType.ACCESS)


def test_wrong_secret_is_rejected() -> None:
    issued = create_access_token(_settings(), subject="1", role="user")
    other = _settings(jwt_secret_key="a-totally-different-secret-key-32bytes!!")
    with pytest.raises(TokenError):
        decode_token(other, issued.token, expected_type=TokenType.ACCESS)


def test_refresh_lives_longer_than_access() -> None:
    s = _settings()
    access = create_access_token(s, subject="1", role="user")
    refresh = create_refresh_token(s, subject="1", role="user")
    assert refresh.expires_at > access.expires_at


# --- settings guard --------------------------------------------------------
def test_production_rejects_default_secret() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_env=AppEnv.PRODUCTION)  # type: ignore[call-arg]


def test_production_accepts_custom_secret() -> None:
    s = Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env=AppEnv.PRODUCTION,
        jwt_secret_key="a-strong-unique-production-secret-32b!!",
    )
    assert s.is_production
