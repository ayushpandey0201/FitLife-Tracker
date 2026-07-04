"""SQLAlchemy repository for stored, revocable refresh tokens.

Only the *hash* of a refresh token is ever persisted (looked up by its ``jti``),
so a database leak does not expose usable tokens. Revocation is a flag flip,
enabling logout and rotate-on-refresh in the auth service.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RefreshToken
from app.logging_config import get_logger

logger = get_logger(__name__)


class SqlAlchemyRefreshTokenRepository:
    """Persistence operations for refresh tokens."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self, *, user_id: int, jti: str, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id, jti=jti, token_hash=token_hash, expires_at=expires_at
        )
        self._session.add(token)
        self._session.flush()
        return token

    def get_by_jti(self, jti: str) -> RefreshToken | None:
        return self._session.scalars(
            select(RefreshToken).where(RefreshToken.jti == jti)
        ).one_or_none()

    def revoke(self, token: RefreshToken) -> None:
        """Mark a token revoked so it can no longer be exchanged."""
        token.revoked = True
        self._session.flush()
        logger.info("refresh_token_revoked jti=%s", token.jti)
