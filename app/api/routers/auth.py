"""Authentication endpoints: register, login, refresh, logout, and whoami.

Routes are deliberately thin — each validates its request via a schema, calls one
:class:`~app.services.auth_service.AuthService` use case, and returns a schema.
Error translation (409/401) is handled centrally in :mod:`app.api.errors`.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.services import AuthServiceDep
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
def register(payload: RegisterRequest, auth: AuthServiceDep) -> UserOut:
    """Register a new user; the email must not already be taken (else 409)."""
    user = auth.register(email=payload.email, password=payload.password)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenPair, summary="Authenticate and get tokens")
def login(payload: LoginRequest, auth: AuthServiceDep) -> TokenPair:
    """Exchange credentials for an access/refresh token pair (401 if invalid)."""
    return auth.login(email=payload.email, password=payload.password)


@router.post("/refresh", response_model=TokenPair, summary="Rotate a refresh token")
def refresh(payload: RefreshRequest, auth: AuthServiceDep) -> TokenPair:
    """Exchange a valid refresh token for a new pair; the old one is revoked."""
    return auth.refresh(payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token",
)
def logout(payload: RefreshRequest, auth: AuthServiceDep) -> None:
    """Revoke the presented refresh token. Idempotent: always returns 204."""
    auth.logout(payload.refresh_token)


@router.get("/me", response_model=UserOut, summary="Current authenticated user")
def me(current_user: CurrentUser) -> UserOut:
    """Return the account tied to the supplied Bearer access token."""
    return UserOut.model_validate(current_user)
