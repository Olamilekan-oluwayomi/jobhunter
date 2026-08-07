"""Telegram Bot API notifications for matched jobs."""

from __future__ import annotations

import html

import requests

from config import Settings
from utils.logger import get_logger
from utils.retry import retry

logger = get_logger("notifications.telegram")

API_BASE = "https://api.telegram.org"


def _fmt(job: dict) -> str:
    title = html.escape(job.get("title") or "Untitled role")
    company = html.escape(job.get("company") or "—")
    location = html.escape(job.get("location") or "—")
    salary = html.escape(job.get("salary") or "—")
    source = html.escape(job.get("source") or "—")
    url = job.get("url") or ""

    return (
        f"🚀 <b>{title}</b>\n"
        f"🏢 {company}\n"
        f"📍 {location}\n"
        f"💰 {salary}\n"
        f"🏷️ {source}\n"
        f"🔗 {html.escape(url)}"
    )


@retry(attempts=3, delay=1.0, backoff=2.0, jitter=0.2, exceptions=(requests.RequestException,))
def _send_message(token: str, chat_id: str, text: str) -> bool:
    response = requests.post(
        f"{API_BASE}/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=10,
    )
    response.raise_for_status()
    return True


def send_telegram(jobs: list[dict], settings: Settings) -> int:
    """Send each job as a Telegram message to the configured chat.

    Returns the number of successfully sent messages. Failures are logged,
    never raised.
    """
    if not settings.telegram_enabled or not jobs:
        return 0

    sent = 0
    for job in jobs:
        try:
            _send_message(
                settings.telegram_bot_token,
                settings.telegram_chat_id,
                _fmt(job),
            )
            sent += 1
        except Exception as exc:
            logger.error("Telegram send failed for %s: %s", job.get("url"), exc)
            continue

    logger.info("Telegram: sent %s message(s) for %s job(s)", sent, len(jobs))
    return sent
