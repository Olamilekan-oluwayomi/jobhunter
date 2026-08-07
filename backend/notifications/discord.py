"""Discord webhook notifications for matched jobs."""

from __future__ import annotations

import requests

from config import Settings
from utils.logger import get_logger
from utils.retry import retry

logger = get_logger("notifications.discord")

MAX_EMBEDS_PER_MESSAGE = 10


@retry(attempts=3, delay=1.0, backoff=2.0, jitter=0.2, exceptions=(requests.RequestException,))
def _post_webhook(url: str, payload: dict) -> None:
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()


def _embed(job: dict) -> dict:
    description = job.get("description") or ""
    if len(description) > 1024:
        description = description[:1021] + "..."

    return {
        "title": job.get("title") or "Untitled role",
        "url": job.get("url"),
        "description": description,
        "color": 0x4F46E5,
        "fields": [
            {"name": "Company", "value": job.get("company") or "—", "inline": True},
            {"name": "Location", "value": job.get("location") or "—", "inline": True},
            {"name": "Salary", "value": job.get("salary") or "—", "inline": True},
            {"name": "Source", "value": job.get("source") or "—", "inline": True},
        ],
        "footer": {"text": "JobHunter"},
        "timestamp": (job.get("posted_at") or ""),
    }


def send_discord(jobs: list[dict], settings: Settings) -> int:
    """Post a Discord webhook message embedding the given jobs.

    Returns the number of successfully posted messages (0 if no webhook
    is configured or every request failed). Failures are logged, never raised.
    """
    if not settings.discord_webhook_url or not jobs:
        return 0

    embeds = [_embed(job) for job in jobs]
    chunks = [
        embeds[i : i + MAX_EMBEDS_PER_MESSAGE]
        for i in range(0, len(embeds), MAX_EMBEDS_PER_MESSAGE)
    ]

    sent = 0
    for chunk in chunks:
        payload = {
            "content": f":mag: **{len(chunk)} matching job(s) found**",
            "embeds": chunk,
        }
        try:
            _post_webhook(settings.discord_webhook_url, payload)
            sent += 1
        except Exception as exc:
            logger.error("Discord webhook failed: %s", exc)
            break

    logger.info("Discord: posted %s message(s) for %s job(s)", sent, len(jobs))
    return sent
