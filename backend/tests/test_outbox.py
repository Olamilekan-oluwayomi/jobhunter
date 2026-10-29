"""Actual database transactions prove exact insertion and durable retry semantics."""

from datetime import timedelta
from unittest.mock import patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from config import Settings
from database.models import Base, Job, NotificationDelivery
from database.repository import insert_new_jobs
from notifications.outbox import drain, enqueue
from utils.time import utcnow


def job(url):
    return {"title": "Python Engineer", "company": "Acme", "source": "Test", "url": url}


def settings(**changes):
    return Settings(
        notifications_enabled=True,
        discord_webhook_url="https://example.invalid/hook",
        telegram_bot_token="",
        telegram_chat_id="",
        match_keywords=[],
        match_min_salary=0,
        match_remote_only=False,
        match_sources=[],
        **changes,
    )


def test_insert_returns_actual_conflict_winners_and_enqueues_atomically():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        insert_new_jobs(db, [job("existing")])
        db.commit()
        inserted = insert_new_jobs(db, [job("existing"), job("new"), job("new")])
        assert [row["url"] for row in inserted] == ["new"]
        enqueue(db, inserted, settings())
        db.rollback()
        assert db.scalar(select(func.count()).select_from(Job)) == 1
        assert db.scalar(select(func.count()).select_from(NotificationDelivery)) == 0
        inserted = insert_new_jobs(db, [job("existing"), job("new")])
        enqueue(db, inserted, settings())
        enqueue(db, inserted, settings())
        db.commit()
        assert db.scalar(select(func.count()).select_from(NotificationDelivery)) == 1
    engine.dispose()


def test_delivery_failure_survives_and_retries_without_resending_successes():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        enqueue(db, insert_new_jobs(db, [job("one"), job("two")]), settings())
        db.commit()
        with patch("notifications.outbox.send_discord", side_effect=[0, 1]) as sender:
            result = drain(db, settings())
            assert sender.call_count == 2
            assert result == {"discord": 1, "telegram": 0, "failed": 1}
        rows = list(db.scalars(select(NotificationDelivery).order_by(NotificationDelivery.id)))
        assert rows[0].status == "pending"
        assert rows[1].status == "sent"
        assert rows[0].attempts == 1
        assert rows[0].next_attempt_at > utcnow()
        rows[0].next_attempt_at = utcnow() - timedelta(seconds=1)
        db.commit()
        with patch("notifications.outbox.send_discord", return_value=1) as sender:
            assert drain(db, settings())["discord"] == 1
            assert sender.call_count == 1
            assert sender.call_args.args[0][0]["url"] == "one"
            assert drain(db, settings())["discord"] == 0
        assert rows[0].attempts == 2
    engine.dispose()


def test_delivery_budget_does_not_discard_pending_jobs():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        config = settings(notify_max_per_run=1)
        enqueue(db, insert_new_jobs(db, [job("one"), job("two")]), config)
        db.commit()
        with patch("notifications.outbox.send_discord", return_value=1):
            assert drain(db, config)["discord"] == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(NotificationDelivery)
                .where(NotificationDelivery.status == "pending")
            )
            == 1
        )
    engine.dispose()
