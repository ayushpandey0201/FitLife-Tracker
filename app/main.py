"""ASGI entrypoint.

Exposes the application instance for ASGI servers:

    uvicorn app.main:app --reload

The app is built via :func:`app.api.app.create_app` using process settings.
"""

from __future__ import annotations

from app.api.app import create_app

app = create_app()
