"""Application configuration (infrastructure).

A single, typed :class:`Settings` object is the one place the application reads
its environment. Centralising configuration here (instead of scattering
``os.getenv`` calls) keeps the pure ``app.domain`` package free of environment
concerns and gives every later phase — persistence, auth, the API — a single,
validated source of truth.

Values are resolved, in order, from: explicit constructor arguments, real
environment variables, then a local ``.env`` file (see ``.env.example``).
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sentinel dev secret. Safe for local development; forbidden in production (see
# the model validator below). Never deploy with this value.
_DEV_JWT_SECRET = "dev-insecure-change-me-please-not-for-production-use"


class AppEnv(StrEnum):
    """The environment the application is running in."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """Supported logging levels (mirrors the standard ``logging`` names)."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Typed application settings, loaded from the environment / ``.env``.

    Fields are added per phase. Later phases (persistence, auth) will add their
    own settings — ``database_url``, ``jwt_secret_key`` — here; they are kept out
    for now to avoid declaring configuration the code does not yet consume.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: AppEnv = AppEnv.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO

    # Persistence (Phase 3). Optional: when unset, no engine is created and the
    # CLI runs statelessly, exactly as before. Example (Postgres via psycopg 3):
    #   postgresql+psycopg://fitlife:fitlife@localhost:5432/fitlife
    database_url: str | None = None

    # Authentication / JWT (Phase 4). ``jwt_secret_key`` MUST be overridden in
    # production (enforced below). Access tokens are short-lived; refresh tokens
    # are longer-lived and revocable (stored, hashed, in the database).
    jwt_secret_key: str = _DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    @property
    def is_production(self) -> bool:
        """True when running in the production environment."""
        return self.app_env is AppEnv.PRODUCTION

    @model_validator(mode="after")
    def _forbid_default_secret_in_production(self) -> Settings:
        """Refuse to boot in production with the insecure default JWT secret."""
        if self.is_production and self.jwt_secret_key == _DEV_JWT_SECRET:
            raise ValueError(
                "jwt_secret_key must be set to a strong, unique value in "
                "production (the built-in default is insecure)."
            )
        return self

    @property
    def require_database_url(self) -> str:
        """Return the configured database URL or raise if it is missing.

        Used by components (repositories, migrations) that cannot function
        without a database, turning a misconfiguration into a clear error.
        """
        if self.database_url is None:
            raise ValueError(
                "database_url is not configured; set DATABASE_URL in the "
                "environment or .env to use persistence."
            )
        return self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings`, constructed once and cached.

    Using a cached accessor (rather than a module-level singleton) keeps import
    side-effect free and lets tests reset configuration via
    ``get_settings.cache_clear()``.
    """
    return Settings()
