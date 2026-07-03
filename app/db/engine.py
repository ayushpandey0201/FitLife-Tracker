"""Engine, session factory, and unit-of-work helper.

The engine and ``sessionmaker`` are built lazily from :class:`~app.config.Settings`
and cached, so importing this module has no side effects and the application only
connects when it actually persists something. Repositories receive a ``Session``
by injection (never a global), which keeps them request-scoped under the future API.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_engine(settings: Settings | None = None) -> Engine:
    """Return the process-wide SQLAlchemy engine, created once and cached.

    Raises ``ValueError`` (via ``require_database_url``) if no database is
    configured — persistence is opt-in.
    """
    resolved = settings or get_settings()
    url = resolved.require_database_url
    # ``pool_pre_ping`` avoids handing out stale connections after DB restarts.
    engine = create_engine(url, pool_pre_ping=True, future=True)
    logger.info("engine_created dialect=%s", engine.dialect.name)
    return engine


@lru_cache(maxsize=1)
def get_sessionmaker(settings: Settings | None = None) -> sessionmaker[Session]:
    """Return the cached session factory bound to the application engine."""
    return sessionmaker(bind=get_engine(settings), expire_on_commit=False, future=True)


@contextmanager
def session_scope(settings: Settings | None = None) -> Iterator[Session]:
    """Provide a transactional session scope (commit on success, rollback on error).

    Intended for scripts/CLI. The API will instead open a session per request.
    """
    session = get_sessionmaker(settings)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
