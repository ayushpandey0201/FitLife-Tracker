"""Service-exception → HTTP-status mapping.

Services raise plain :class:`~app.services.exceptions.ServiceError` subclasses and
never import HTTP types (see that module). This is the single place that turns
each into an ``application/json`` error response, so routers stay free of
try/except plumbing. Register the handlers via :func:`register_error_handlers`.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    PlanNotFoundError,
    ProfileNotFoundError,
    ServiceError,
)

# Each service error maps to exactly one status code. 401s advertise Bearer auth.
_STATUS_BY_ERROR: dict[type[ServiceError], int] = {
    EmailAlreadyExistsError: status.HTTP_409_CONFLICT,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InvalidTokenError: status.HTTP_401_UNAUTHORIZED,
    ProfileNotFoundError: status.HTTP_404_NOT_FOUND,
    PlanNotFoundError: status.HTTP_404_NOT_FOUND,
}


def _service_error_handler(_request: Request, exc: ServiceError) -> JSONResponse:
    """Translate a service error into its mapped JSON response."""
    code = _STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST)
    headers = {"WWW-Authenticate": "Bearer"} if code == status.HTTP_401_UNAUTHORIZED else None
    return JSONResponse(status_code=code, content={"detail": str(exc)}, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    """Install the service-exception handlers on ``app``.

    A single handler on the :class:`ServiceError` base covers every subclass
    (including ones added later); the mapping above refines the status code.
    """
    app.add_exception_handler(ServiceError, _service_error_handler)  # type: ignore[arg-type]
