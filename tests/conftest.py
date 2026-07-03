"""Shared pytest fixtures.

Provides an isolated, in-memory SQLite database per test so the repository layer
is exercised end-to-end (engine → session → ORM → mapping) without any external
service. The schema is created from ``Base.metadata`` — the same metadata Alembic
migrates in production — so tests validate the real table definitions.
"""

from __future__ import annotations

from collections.abc import Iterator

# Import models so their tables register on Base.metadata before create_all.
import app.db.models  # noqa: F401
import pytest
from app.db.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Yield a session bound to a fresh in-memory SQLite database."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
