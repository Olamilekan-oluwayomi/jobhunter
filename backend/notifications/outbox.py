"""Transactional outbox with per-job/channel delivery state and bounded retries.

Delivery is at least once: a crash after the provider accepts a message but before
the database commits can repeat it. Neither provider offers a shared idempotency key.
"""

import json
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from config import get_settings
from database.models import NotificationDelivery
from notifications.discord import send_discord
from notifications.matcher import matches_any
from notifications.telegram import send_telegram
from utils.time import utcnow


def enqueue(db, jobs, settings=None):
    """Called inside the job-insert transaction; does not commit."""
    settings = settings or get_settings()
    if not settings.any_channel_enabled:
        return 0
    channels = (["discord"] if settings.discord_enabled else []) + (
        ["telegram"] if settings.telegram_enabled else []
    )
    rows = []
    matched = 0
    for job in jobs:
        if not matches_any(job, settings):
            continue
        matched += 1
        for channel in channels:
            rows.append(
                {
                    "job_id": job["id"],
                    "channel": channel,
                    "payload": json.dumps(job, default=str),
                    "attempts": 0,
                    "status": "pending",
                    "next_attempt_at": utcnow(),
                }
            )
    if rows:
        insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
        db.execute(
            insert(NotificationDelivery).on_conflict_do_nothing(
                index_elements=[NotificationDelivery.job_id, NotificationDelivery.channel]
            ),
            rows,
        )
    return matched


def drain(db, settings=None):
    """Claim with row locks; failed deliveries survive and retry on later drains."""
    settings = settings or get_settings()
    counts = {"discord": 0, "telegram": 0, "failed": 0}
    if not settings.any_channel_enabled:
        return counts
    channels = (["discord"] if settings.discord_enabled else []) + (
        ["telegram"] if settings.telegram_enabled else []
    )
    limit = settings.notify_max_per_run or 100
    for _ in range(limit):
        delivery = db.scalar(
            select(NotificationDelivery)
            .where(
                NotificationDelivery.status == "pending",
                NotificationDelivery.channel.in_(channels),
                NotificationDelivery.next_attempt_at <= utcnow(),
            )
            .order_by(NotificationDelivery.next_attempt_at, NotificationDelivery.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if delivery is None:
            db.rollback()
            break
        delivery.attempts += 1
        try:
            sender = send_discord if delivery.channel == "discord" else send_telegram
            success = sender([json.loads(delivery.payload)], settings) == 1
        except Exception:
            success = False
        if success:
            delivery.status = "sent"
            delivery.sent_at = utcnow()
            delivery.last_error = None
            counts[delivery.channel] += 1
        else:
            delivery.status = "failed" if delivery.attempts >= 8 else "pending"
            delivery.last_error = "Provider did not confirm delivery"
            delivery.next_attempt_at = utcnow() + timedelta(
                seconds=min(60 * 2 ** (delivery.attempts - 1), 3600)
            )
            counts["failed"] += 1
        db.commit()
    return counts
