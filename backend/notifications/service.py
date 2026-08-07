"""Notification service: match new jobs and fan them out to channels."""

from __future__ import annotations

from dataclasses import dataclass

from config import Settings, get_settings
from notifications.discord import send_discord
from notifications.matcher import matches_any
from notifications.telegram import send_telegram
from utils.logger import get_logger

logger = get_logger("notifications.service")


@dataclass(frozen=True)
class NotificationReport:
    matched: int
    discord_sent: int = 0
    telegram_sent: int = 0


def notify_new_jobs(
    jobs: list[dict],
    settings: Settings | None = None,
) -> NotificationReport:
    """Filter the given (new) jobs by the configured matching rules and send
    notifications to every enabled channel for those that pass.

    A job is only ever *sent* when it matched the rules AND notifications are
    enabled AND at least one channel is configured. Nothing is raised here;
    per-channel send functions swallow their own failures.
    """
    settings = settings or get_settings()

    if not settings.any_channel_enabled:
        logger.info("Notifications disabled — skipping.")
        return NotificationReport(matched=0)

    matched: list[dict] = []
    for job in jobs:
        if matches_any(job, settings):
            matched.append(job)

    if not matched:
        logger.info("No jobs matched the configured rules.")
        return NotificationReport(matched=0)

    if settings.notify_max_per_run and len(matched) > settings.notify_max_per_run:
        logger.warning(
            "Truncating %s matched jobs to %s for this notification run.",
            len(matched),
            settings.notify_max_per_run,
        )
        matched = matched[: settings.notify_max_per_run]

    discord_sent = send_discord(matched, settings) if settings.discord_enabled else 0
    telegram_sent = send_telegram(matched, settings) if settings.telegram_enabled else 0

    logger.info(
        "%s job(s) matched; discord=%s telegram=%s",
        len(matched),
        discord_sent,
        telegram_sent,
    )
    return NotificationReport(
        matched=len(matched),
        discord_sent=discord_sent,
        telegram_sent=telegram_sent,
    )
