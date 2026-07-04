"""JWT access & refresh token creation and verification (PyJWT).

Tokens are signed with the application secret and carry a ``type`` claim so an
access token can never be used where a refresh token is required (and vice
versa). Each token has a unique ``jti`` — for refresh tokens this is what the
database stores (hashed) to support revocation and rotation.

These helpers are pure functions of their inputs plus the current time; all
policy (expiry, algorithm, secret) comes from :class:`~app.config.Settings`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import uuid4

import jwt

from app.config import Settings


class TokenType(StrEnum):
    """Discriminates access tokens from refresh tokens via the ``type`` claim."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    """Raised when a token is invalid, expired, or of an unexpected type."""


@dataclass(frozen=True)
class DecodedToken:
    """The validated, structured payload of a decoded token."""

    subject: str
    role: str
    token_type: TokenType
    jti: str
    expires_at: datetime


@dataclass(frozen=True)
class IssuedToken:
    """A freshly minted token plus the metadata a caller may need to persist."""

    token: str
    jti: str
    expires_at: datetime


def _encode(
    *,
    settings: Settings,
    subject: str,
    role: str,
    token_type: TokenType,
    lifetime: timedelta,
) -> IssuedToken:
    now = datetime.now(UTC)
    expires_at = now + lifetime
    jti = uuid4().hex
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type.value,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return IssuedToken(token=token, jti=jti, expires_at=expires_at)


def create_access_token(settings: Settings, *, subject: str, role: str) -> IssuedToken:
    """Mint a short-lived access token for ``subject`` (the user id) and ``role``."""
    return _encode(
        settings=settings,
        subject=subject,
        role=role,
        token_type=TokenType.ACCESS,
        lifetime=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(settings: Settings, *, subject: str, role: str) -> IssuedToken:
    """Mint a longer-lived refresh token; its ``jti`` is stored for revocation."""
    return _encode(
        settings=settings,
        subject=subject,
        role=role,
        token_type=TokenType.REFRESH,
        lifetime=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(settings: Settings, token: str, *, expected_type: TokenType) -> DecodedToken:
    """Validate a token's signature, expiry, and type; return its payload.

    Raises :class:`TokenError` on any invalid, expired, or mismatched-type token.
    """
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc

    if claims.get("type") != expected_type.value:
        raise TokenError(f"expected a {expected_type.value} token, got {claims.get('type')!r}")

    return DecodedToken(
        subject=claims["sub"],
        role=claims.get("role", "user"),
        token_type=expected_type,
        jti=claims["jti"],
        expires_at=datetime.fromtimestamp(claims["exp"], tz=UTC),
    )
