"""Tests for the notification service fan-out logic."""

from __future__ import annotations

from unittest.mock import patch

from config import Settings
from notifications.service import NotificationReport, notify_new_jobs


def _settings(**overrides):
    base = {
        "notifications_enabled": True,
        "discord_webhook_url": "https://hooks.example.com/abc",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "notify_max_per_run": 5,
        "match_keywords": ["go"],
        "match_sources": [],
        "match_require_all_keywords": False,
        "match_remote_only": False,
        "match_min_salary": 0,
    }
    base.update(overrides)
    return Settings(**base)


def _job(title="Go Engineer", source="Remotive") -> dict:
    return {
        "title": title,
        "company": "Acme",
        "location": "Remote",
        "salary": "",
        "description": "Backend role in Go.",
        "source": source,
        "url": f"https://example.com/job/{title}-{source}",
    }


def test_disabled_notifications_return_empty_report():
    settings = _settings(notifications_enabled=False)
    report = notify_new_jobs([], settings)
    assert report == NotificationReport(matched=0)


def test_no_channels_configured_returns_zero(monkeypatch):
    settings = _settings(
        discord_webhook_url="",
        telegram_bot_token="",
        telegram_chat_id="",
    )
    report = notify_new_jobs([_job()], settings)
    assert report == NotificationReport(matched=0)


def test_discord_only_channel():
    settings = _settings()
    with (
        patch("notifications.service.send_discord", return_value=1) as discord_mock,
        patch("notifications.service.send_telegram", return_value=0) as tg_mock,
    ):
        report = notify_new_jobs([_job()], settings)
    discord_mock.assert_called_once()
    tg_mock.assert_not_called()
    assert report == NotificationReport(matched=1, discord_sent=1)


def test_both_channels_called():
    settings = _settings(
        telegram_bot_token="123:ABC",
        telegram_chat_id="42",
    )
    with (
        patch("notifications.service.send_discord", return_value=1) as discord_mock,
        patch("notifications.service.send_telegram", return_value=1) as tg_mock,
    ):
        report = notify_new_jobs([_job()], settings)
    discord_mock.assert_called_once()
    tg_mock.assert_called_once()
    assert report == NotificationReport(matched=1, discord_sent=1, telegram_sent=1)


def test_non_matching_jobs_are_not_sent():
    settings = _settings(match_keywords=["golang"])
    with (
        patch("notifications.service.send_discord") as discord_mock,
        patch("notifications.service.send_telegram") as tg_mock,
    ):
        report = notify_new_jobs([_job(title="React Frontend Dev")], settings)
    discord_mock.assert_not_called()
    tg_mock.assert_not_called()
    assert report.matched == 0


def test_max_per_run_truncates():
    settings = _settings(notify_max_per_run=2)
    jobs = [_job(title=f"Python Dev {i}") for i in range(10)]
    with patch("notifications.service.send_discord", return_value=1) as discord_mock:
        report = notify_new_jobs(jobs, settings)
    sent_jobs = discord_mock.call_args.args[0]
    assert len(sent_jobs) == 2
    assert report.matched == 2
