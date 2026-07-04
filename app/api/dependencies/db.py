"""Request-scoped database session dependency.

Yields one session per request and commits on success / rolls back on error, so
services never manage transactions themselves. Tests override this provider to
bind an in-memory SQLite session.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db.engine import get_sessionmaker


def get_db() -> Iterator[Session]:
    """Provide a transactional :class:`Session` for the lifetime of a request."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
