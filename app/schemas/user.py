"""User response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserOut(BaseModel):
    """Public representation of a user account (never exposes the password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
