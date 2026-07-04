"""Alembic environment.

The database URL and target metadata come from the application itself
(``app.config.Settings`` and ``app.db.base.Base``) rather than being duplicated
in ``alembic.ini`` — the app stays the single source of truth. Importing the ORM
models registers their tables on ``Base.metadata`` for autogenerate.
"""

from __future__ import annotations

from logging.config import fileConfig

# Import models so their tables are registered on Base.metadata.
import app.db.models  # noqa: F401
from alembic import context
from app.config import get_settings
from app.db.base import Base
from sqlalchemy import engine_from_config, pool

config = context.config

# Resolve the connection URL from application settings (env / .env).
config.set_main_option("sqlalchemy.url", get_settings().require_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emits SQL)."""
    url = config.get_main_option("sqlalchemy.url") or ""
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        # SQLite cannot ALTER in place; batch mode rebuilds the table instead.
        render_as_batch=url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # Batch (table-rebuild) migrations only where the backend needs them.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
