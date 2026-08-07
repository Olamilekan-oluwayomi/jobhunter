"""Centralised runtime configuration loaded from environment variables.

All runtime behaviour is driven by environment variables (see ``.env.example``).
Defaults are safe for local development; production deployments override them
via the Docker compose environment block.

Matcher settings define which newly scraped jobs are worth notifying about.
A job is "matched" when any of its text fields contains every *required*
keyword, or — when require_all is False — at least one keyword.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load the .env file next to this module (repository root) if present.
ENV_FILE = Path(__file__).resolve().parents[0] / ".env"
load_dotenv(ENV_FILE)


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _list(name: str) -> list[str]:
    return [part.strip() for part in os.getenv(name, "").split(",") if part.strip()]


def _database_url() -> str:
    """Build a PostgreSQL URL from either DATABASE_URL or the DB_* parts."""
    explicit = _str("DATABASE_URL")
    if explicit:
        return explicit
    return (
        f"postgresql://{_str('DB_USER', 'postgres')}:"
        f"{_str('DB_PASSWORD', '')}@"
        f"{_str('DB_HOST', 'localhost')}:{_int('DB_PORT', 5432)}/"
        f"{_str('DB_NAME', 'jobhunter')}"
    )


@dataclass(frozen=True)
class Settings:
    """Production runtime settings for the whole application."""

    # --- app ---
    app_name: str = field(default_factory=lambda: _str("APP_NAME", "JobHunter"))
    app_version: str = field(default_factory=lambda: _str("APP_VERSION", "1.0.0"))
    environment: str = field(default_factory=lambda: _str("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: _bool("DEBUG", False))
    api_prefix: str = field(default_factory=lambda: _str("API_PREFIX", ""))
    db_url: str = field(default_factory=_database_url)
    db_echo: bool = field(default_factory=lambda: _bool("DB_ECHO", False))

    # --- logging ---
    log_level: str = field(default_factory=lambda: _str("LOG_LEVEL", "INFO"))
    log_format: str = field(
        default_factory=lambda: _str(
            "LOG_FORMAT", "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    )

    # --- security / HTTP ---
    cors_origins: list[str] = field(
        default_factory=lambda: _list(
            "CORS_ORIGINS",
        )
    )
    # Default origins for local development frontends.
    DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )
    trusted_hosts: list[str] = field(
        default_factory=lambda: _list("TRUSTED_HOSTS") or ["localhost", "127.0.0.1", "0.0.0.0"]
    )

    # --- rate limiting ---
    rate_limit_enabled: bool = field(default_factory=lambda: _bool("RATE_LIMIT_ENABLED", True))
    rate_limit_requests: int = field(default_factory=lambda: _int("RATE_LIMIT_REQUESTS", 120))
    rate_limit_window_seconds: int = field(
        default_factory=lambda: _int("RATE_LIMIT_WINDOW_SECONDS", 60)
    )

    # --- scrapers ---
    scraper_timeout: float = field(default_factory=lambda: _float("SCRAPER_TIMEOUT", 15.0))
    scraper_max_retries: int = field(default_factory=lambda: _int("SCRAPER_MAX_RETRIES", 3))
    reddit_enabled: bool = field(default_factory=lambda: _bool("REDDIT_ENABLED", True))
    reddit_timeout: float = field(default_factory=lambda: _float("REDDIT_TIMEOUT", 10.0))
    reddit_max_retries: int = field(default_factory=lambda: _int("REDDIT_MAX_RETRIES", 0))
    upwork_enabled: bool = field(default_factory=lambda: _bool("UPWORK_ENABLED", True))
    upwork_timeout: float = field(default_factory=lambda: _float("UPWORK_TIMEOUT", 15.0))
    upwork_max_retries: int = field(default_factory=lambda: _int("UPWORK_MAX_RETRIES", 2))

    # --- scheduler ---
    schedule_enabled: bool = field(default_factory=lambda: _bool("SCHEDULE_ENABLED", True))
    schedule_interval_minutes: int = field(
        default_factory=lambda: _int("SCHEDULE_INTERVAL_MINUTES", 60)
    )
    run_on_startup: bool = field(default_factory=lambda: _bool("SCHEDULE_RUN_ON_STARTUP", True))

    # --- notifications ---
    discord_webhook_url: str = field(default_factory=lambda: _str("DISCORD_WEBHOOK_URL"))
    telegram_bot_token: str = field(default_factory=lambda: _str("TELEGRAM_BOT_TOKEN"))
    telegram_chat_id: str = field(default_factory=lambda: _str("TELEGRAM_CHAT_ID"))
    notifications_enabled: bool = field(
        default_factory=lambda: _bool("NOTIFICATIONS_ENABLED", True)
    )
    notify_max_per_run: int = field(default_factory=lambda: _int("NOTIFY_MAX_PER_RUN", 20))

    # --- job matching ---
    match_keywords: list[str] = field(default_factory=lambda: _list("MATCH_KEYWORDS"))
    match_sources: list[str] = field(default_factory=lambda: _list("MATCH_SOURCES"))
    match_require_all_keywords: bool = field(
        default_factory=lambda: _bool("MATCH_REQUIRE_ALL_KEYWORDS", False)
    )
    match_remote_only: bool = field(default_factory=lambda: _bool("MATCH_REMOTE_ONLY", False))
    match_min_salary: int = field(default_factory=lambda: _int("MATCH_MIN_SALARY", 0))

    # --- properties ---
    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}

    @property
    def discord_enabled(self) -> bool:
        return bool(self.discord_webhook_url)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def any_channel_enabled(self) -> bool:
        return self.notifications_enabled and (self.discord_enabled or self.telegram_enabled)

    @property
    def matcher_configured(self) -> bool:
        return bool(
            self.match_keywords
            or self.match_sources
            or self.match_remote_only
            or self.match_min_salary
        )

    @property
    def effective_cors_origins(self) -> list[str]:
        origins = list(self.cors_origins) if self.cors_origins else []
        if not self.is_production:
            origins = list(self.DEFAULT_CORS_ORIGINS) + origins
        return list(dict.fromkeys(origins))


def get_settings() -> Settings:
    """Return the current runtime settings (cached instance)."""
    if not hasattr(get_settings, "_cache"):
        get_settings._cache = Settings()
    return get_settings._cache


def reload_settings() -> Settings:
    """Re-read settings from the environment (used by tests)."""
    if hasattr(get_settings, "_cache"):
        del get_settings._cache
    return get_settings()
