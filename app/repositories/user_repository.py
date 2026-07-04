"""SQLAlchemy repository for :class:`~app.db.models.User` accounts.

The user record is an authentication aggregate with no pure-domain counterpart,
so this repository returns the ORM entity directly (within the caller's unit of
work). Password hashing and token policy live in the service layer, never here —
repositories only read and write.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.logging_config import get_logger

logger = get_logger(__name__)


class SqlAlchemyUserRepository:
    """Persistence operations for user accounts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, *, email: str, hashed_password: str, role: str = "user") -> User:
        user = User(email=email, hashed_password=hashed_password, role=role)
        self._session.add(user)
        self._session.flush()
        logger.info("user_created id=%d", user.id)
        return user

    def get_by_id(self, user_id: int) -> User | None:
        return self._session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._session.scalars(select(User).where(User.email == email)).one_or_none()
