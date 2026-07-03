"""Centralised logging configuration (infrastructure).

The application configures logging exactly once, at an entrypoint (the CLI
today; the FastAPI app later), driven by :class:`~app.config.Settings`. Library
and domain code never call :func:`logging.basicConfig` — they only ever obtain a
named logger via :func:`logging.getLogger(__name__)` and log to it, so the
entrypoint stays in full control of handlers, level and format.

The format is intentionally plain, structured key=value text: readable in a
terminal today and trivial to swap for JSON once logs are shipped to a log
aggregator in a later phase.
"""

from __future__ import annotations

import logging

from app.config import LogLevel, Settings, get_settings

# key=value line format — greppable and aggregator-friendly.
_LOG_FORMAT = "%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

# Guards against re-installing handlers if configuration runs more than once
# (e.g. tests, or a reload). Idempotency keeps output free of duplicate lines.
_configured = False


def configure_logging(settings: Settings | None = None, *, force: bool = False) -> None:
    """Initialise the root logger from settings. Safe to call more than once.

    Args:
        settings: Configuration to use; defaults to the cached application
            settings via :func:`~app.config.get_settings`.
        force: Reconfigure even if logging was already set up (mainly for tests).
    """
    global _configured
    if _configured and not force:
        return

    resolved = settings or get_settings()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(_to_level(resolved.log_level))

    _configured = True


def _to_level(level: LogLevel) -> int:
    """Translate our :class:`~app.config.LogLevel` to a ``logging`` int level."""
    return logging.getLevelNamesMapping()[level.value]


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Thin wrapper to standardise how modules obtain one."""
    return logging.getLogger(name)
