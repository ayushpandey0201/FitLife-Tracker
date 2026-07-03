"""Database infrastructure: declarative base, engine/session, ORM models.

This package is the only place that imports SQLAlchemy. The pure ``app.domain``
layer never depends on it — persistence is reached through the repository port
(:class:`app.domain.repositories.ProfileRepository`).
"""
