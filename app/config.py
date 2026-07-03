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

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def is_production(self) -> bool:
        """True when running in the production environment."""
        return self.app_env is AppEnv.PRODUCTION


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings`, constructed once and cached.

    Using a cached accessor (rather than a module-level singleton) keeps import
    side-effect free and lets tests reset configuration via
    ``get_settings.cache_clear()``.
    """
    return Settings()
