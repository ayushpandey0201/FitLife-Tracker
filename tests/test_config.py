"""Tests for the configuration layer (app.config)."""

from __future__ import annotations

import pytest
from app.config import AppEnv, LogLevel, Settings, get_settings


def test_defaults_when_env_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no env vars / .env, sensible defaults apply."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_env is AppEnv.DEVELOPMENT
    assert settings.log_level is LogLevel.INFO
    assert settings.is_production is False


def test_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_env is AppEnv.PRODUCTION
    assert settings.log_level is LogLevel.WARNING
    assert settings.is_production is True


def test_env_values_are_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("app_env", "testing")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_env is AppEnv.TESTING


def test_invalid_value_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "not-a-level")
    with pytest.raises(ValueError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
    get_settings.cache_clear()
