"""Repository adapters — concrete implementations of the domain ports.

Adapters live here (infrastructure), depend on SQLAlchemy, and translate between
ORM rows and pure domain models. The domain never imports this package; it only
depends on the abstract ports in :mod:`app.domain.repositories`.
"""
