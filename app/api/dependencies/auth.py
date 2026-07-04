"""Authentication & authorization dependencies.

Extracts and validates the Bearer access token, loads the current active user,
and offers an RBAC-ready ``require_role`` factory. Only the ``user`` role exists
today, but role checks are wired so adding ``admin`` later needs no plumbing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.api.dependencies.db import get_db
from app.config import Settings, get_settings
from app.db.models import User
from app.repositories.user_repository import SqlAlchemyUserRepository
from app.security.tokens import TokenError, TokenType, decode_token

# tokenUrl documents the login endpoint for Swagger's "Authorize" dialog.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def provide_settings() -> Settings:
    """Expose application settings as a dependency (overridable in tests)."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(provide_settings)]
SessionDep = Annotated[Session, Depends(get_db)]


def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
    session: SessionDep,
    settings: SettingsDep,
) -> User:
    """Resolve the authenticated, active user from a Bearer access token."""
    try:
        decoded = decode_token(settings, token, expected_type=TokenType.ACCESS)
    except TokenError as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    user = SqlAlchemyUserRepository(session).get_by_id(int(decoded.subject))
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):  # type: ignore[no-untyped-def]
    """Build a dependency that admits only users holding one of ``roles``."""

    def _dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _dependency
