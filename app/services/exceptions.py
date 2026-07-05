"""Application-service exceptions.

These represent use-case-level failures (authentication, conflicts) as opposed to
pure domain-rule violations (:mod:`app.domain.exceptions`). The API layer maps
each to an HTTP status; keeping them here means services never import HTTP types.
"""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for recoverable application-service errors."""


class EmailAlreadyExistsError(ServiceError):
    """Raised when registering an email that is already taken (→ HTTP 409)."""


class InvalidCredentialsError(ServiceError):
    """Raised when login credentials do not match (→ HTTP 401)."""


class InvalidTokenError(ServiceError):
    """Raised when a refresh token is missing, expired, or revoked (→ HTTP 401)."""


class ProfileNotFoundError(ServiceError):
    """Raised when a required profile does not exist for the user (→ HTTP 404)."""


class PlanNotFoundError(ServiceError):
    """Raised when a requested plan does not exist for the user (→ HTTP 404)."""


class LogNotFoundError(ServiceError):
    """Raised when a tracking log to delete does not exist for the user (→ 404)."""


class UnknownExerciseError(ServiceError):
    """Raised when a logged exercise is not in the catalogue (→ HTTP 404)."""
