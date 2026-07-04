"""Authentication request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload to create a new account."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128, description="Plain password")


class LoginRequest(BaseModel):
    """Payload to authenticate and obtain tokens (JSON, mobile-friendly)."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """Payload to exchange a valid refresh token for a new token pair."""

    refresh_token: str


class TokenPair(BaseModel):
    """Issued access + refresh tokens returned by login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access-token lifetime in seconds")
