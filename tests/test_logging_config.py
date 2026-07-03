"""Tests for centralised logging configuration (app.logging_config)."""

from __future__ import annotations

import logging

from app.config import LogLevel, Settings
from app.logging_config import configure_logging, get_logger


def _settings(level: LogLevel) -> Settings:
    return Settings(_env_file=None, log_level=level)  # type: ignore[call-arg]


def test_configure_sets_root_level() -> None:
    configure_logging(_settings(LogLevel.WARNING), force=True)
    assert logging.getLogger().level == logging.WARNING
    configure_logging(_settings(LogLevel.INFO), force=True)
    assert logging.getLogger().level == logging.INFO


def test_configure_is_idempotent_without_force() -> None:
    configure_logging(_settings(LogLevel.INFO), force=True)
    handler_count = len(logging.getLogger().handlers)
    # Repeated non-forced calls must not stack handlers (=> duplicate lines).
    configure_logging(_settings(LogLevel.INFO))
    assert len(logging.getLogger().handlers) == handler_count


def test_logger_respects_configured_level() -> None:
    configure_logging(_settings(LogLevel.INFO), force=True)
    log = get_logger("test.sample")
    # DEBUG is below the configured INFO threshold, so it is filtered out.
    assert log.isEnabledFor(logging.INFO)
    assert not log.isEnabledFor(logging.DEBUG)
