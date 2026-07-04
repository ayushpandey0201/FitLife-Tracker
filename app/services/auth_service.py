"""Authentication service: registration, login, refresh rotation, logout.

Orchestrates the user + refresh-token repositories and the security primitives.
Refresh tokens are persisted **hashed** and looked up by ``jti``; refreshing
*rotates* (revokes the presented token and issues a new pair) so a leaked
refresh token has a short useful life and can be cut off by logout.
"""

from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import User
from app.logging_config import get_logger
from app.repositories.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from app.repositories.user_repository import SqlAlchemyUserRepository
from app.schemas.auth import TokenPair
from app.security.password import hash_password, verify_password
from app.security.tokens import (
    DecodedToken,
    TokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)

logger = get_logger(__name__)


def _hash_token(token: str) -> str:
    """One-way hash for storing a refresh token (a high-entropy JWT)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    """Use cases for authentication and token lifecycle."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self._settings = settings
        self._users = SqlAlchemyUserRepository(session)
        self._refresh_tokens = SqlAlchemyRefreshTokenRepository(session)

    # -- registration / login ------------------------------------------------
    def register(self, *, email: str, password: str) -> User:
        """Create a new account, rejecting a duplicate email."""
        if self._users.get_by_email(email) is not None:
            raise EmailAlreadyExistsError(email)
        user = self._users.add(email=email, hashed_password=hash_password(password))
        logger.info("user_registered id=%d", user.id)
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        """Return the user for valid, active credentials, else raise."""
        user = self._users.get_by_email(email)
        if user is None or not user.is_active:
            raise InvalidCredentialsError(email)
        if not verify_password(user.hashed_password, password):
            raise InvalidCredentialsError(email)
        return user

    def login(self, *, email: str, password: str) -> TokenPair:
        """Authenticate and issue a fresh access/refresh token pair."""
        user = self.authenticate(email=email, password=password)
        return self._issue_pair(user)

    # -- token lifecycle -----------------------------------------------------
    def refresh(self, refresh_token: str) -> TokenPair:
        """Validate a refresh token and rotate it for a new pair."""
        decoded = self._decode_refresh(refresh_token)
        stored = self._refresh_tokens.get_by_jti(decoded.jti)
        if (
            stored is None
            or stored.revoked
            or stored.token_hash != _hash_token(refresh_token)
        ):
            raise InvalidTokenError("refresh token is not recognised or revoked")

        user = self._users.get_by_id(int(decoded.subject))
        if user is None or not user.is_active:
            raise InvalidTokenError("account is unavailable")

        # Rotate: the presented token can never be used again.
        self._refresh_tokens.revoke(stored)
        return self._issue_pair(user)

    def logout(self, refresh_token: str) -> None:
        """Revoke a refresh token. Idempotent: unknown/invalid tokens are no-ops."""
        try:
            decoded = self._decode_refresh(refresh_token)
        except InvalidTokenError:
            return
        stored = self._refresh_tokens.get_by_jti(decoded.jti)
        if stored is not None and not stored.revoked:
            self._refresh_tokens.revoke(stored)

    # -- helpers -------------------------------------------------------------
    def _decode_refresh(self, token: str) -> DecodedToken:
        try:
            return decode_token(self._settings, token, expected_type=TokenType.REFRESH)
        except TokenError as exc:
            raise InvalidTokenError(str(exc)) from exc

    def _issue_pair(self, user: User) -> TokenPair:
        subject = str(user.id)
        access = create_access_token(self._settings, subject=subject, role=user.role)
        refresh = create_refresh_token(self._settings, subject=subject, role=user.role)
        self._refresh_tokens.add(
            user_id=user.id,
            jti=refresh.jti,
            token_hash=_hash_token(refresh.token),
            expires_at=refresh.expires_at,
        )
        return TokenPair(
            access_token=access.token,
            refresh_token=refresh.token,
            expires_in=self._settings.access_token_expire_minutes * 60,
        )
