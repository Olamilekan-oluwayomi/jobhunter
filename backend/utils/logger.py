"""Logging configuration.

Production setup: console output at the configured level (default INFO),
plus an optional rotating file handler when ``LOG_FILE`` is set. The format
can be overridden with ``LOG_FORMAT``.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

_configured = False


def configure_logging(level: str | int | None = None) -> None:
    """Configure root logging. Safe to call multiple times."""
    global _configured

    from config import get_settings

    settings = get_settings()
    if level is not None:
        log_level = level
    else:
        raw = os.getenv("LOG_LEVEL") or settings.log_level or "INFO"
        log_level = logging.getLevelName(raw.upper())

    log_format = os.getenv("LOG_FORMAT") or settings.log_format or DEFAULT_FORMAT
    log_file = os.getenv("LOG_FILE", "").strip()

    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(
            RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
        )

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True,
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger (configures logging on first use)."""
    if not _configured:
        configure_logging()
    return logging.getLogger(name)
