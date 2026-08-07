"""Tests for the configuration layer."""

from __future__ import annotations

from config import reload_settings


def test_defaults_are_local_dev_safe(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    settings = reload_settings()
    assert settings.environment == "development"
    assert settings.app_name == "JobHunter"
    assert settings.debug is False
    assert settings.api_prefix == ""
    assert settings.rate_limit_requests > 0


def test_is_production_only_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    reload_settings()
    assert reload_settings().is_production is True

    monkeypatch.setenv("ENVIRONMENT", "staging")
    assert reload_settings().is_production is False


def test_database_url_built_from_parts(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_USER", "me")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    monkeypatch.setenv("DB_HOST", "db.example.com")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "hunter")
    url = reload_settings().db_url
    assert url == "postgresql://me:secret@db.example.com:5433/hunter"


def test_effective_cors_origins_include_defaults_in_dev(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    settings = reload_settings()
    assert "http://localhost:5173" in settings.effective_cors_origins


def test_effective_cors_origins_no_defaults_in_prod(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://jobs.example.com")
    settings = reload_settings()
    assert settings.effective_cors_origins == ["https://jobs.example.com"]
    assert "http://localhost:5173" not in settings.effective_cors_origins


def test_notification_channels(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    settings = reload_settings()
    assert settings.any_channel_enabled is False

    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://hooks.example.com/abc")
    assert reload_settings().discord_enabled is True


def test_bool_env_parsing(monkeypatch):
    monkeypatch.setenv("NOTIFICATIONS_ENABLED", "1")
    assert reload_settings().notifications_enabled is True
    monkeypatch.setenv("NOTIFICATIONS_ENABLED", "false")
    assert reload_settings().notifications_enabled is False
    monkeypatch.setenv("NOTIFICATIONS_ENABLED", "garbage")
    assert reload_settings().notifications_enabled is False
