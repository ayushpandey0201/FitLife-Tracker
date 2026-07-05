"""FastAPI application factory.

:func:`create_app` assembles the HTTP adapter: it configures logging once, mounts
the resource routers, and installs the service-exception handlers. Using a factory
(rather than a module-level app built at import time) keeps construction explicit
and lets tests build an app with overridden dependencies. A module-level
:data:`app` is provided for ``uvicorn app.main:app``.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routers import auth, logs, plan, profile, progress, recommendations
from app.config import Settings, get_settings
from app.logging_config import configure_logging

_TITLE = "FitLife Tracker API"
_DESCRIPTION = "Authentication, user fitness profiles, and deterministic nutrition plans."


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=_TITLE,
        description=_DESCRIPTION,
        version="0.4.0",
    )

    register_error_handlers(app)

    for router in (
        auth.router,
        profile.router,
        plan.router,
        logs.router,
        progress.router,
        recommendations.router,
    ):
        app.include_router(router)

    @app.get("/health", tags=["meta"], summary="Liveness probe")
    def health() -> dict[str, str]:
        """Return a static OK payload for liveness/readiness checks."""
        return {"status": "ok"}

    return app
