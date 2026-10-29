"""Opt-in PostgreSQL verification in a unique, disposable schema.

Set TEST_DATABASE_URL to a database where the test role may create schemas.
No existing tables are read or changed; all objects live in the generated schema.
"""

import os
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from config import Settings
from database.models import NotificationDelivery, User
from database.repository import insert_new_jobs
from matching.discovery import discover
from notifications.outbox import drain, enqueue

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


def test_migration_preserves_legacy_data_and_postgres_constraints():
    url = make_url(os.environ["TEST_DATABASE_URL"])
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg2")
    schema = "jobhunter_verify_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = url.update_query_dict({"options": f"-csearch_path={schema}"})
    engine = create_engine(scoped_url)
    env = {**os.environ, "DATABASE_URL": scoped_url.render_as_string(hide_password=False)}
    root = Path(__file__).resolve().parents[1]

    def migrate(revision):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Do not print environment variables or connection URLs on failure.
        output = result.stderr.replace(env["DATABASE_URL"], "[database URL]")
        if url.password:
            output = output.replace(url.password, "[redacted]")
        assert result.returncode == 0, output

    try:
        migrate("0005_application_statuses")
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO sources(name) VALUES ('Test')"))
            connection.execute(
                text(
                    "INSERT INTO jobs(title,company,url,source) "
                    "VALUES ('Engineer','Acme','https://example.invalid/1','Test')"
                )
            )
            connection.execute(text("INSERT INTO saved_jobs(job_id) VALUES (1)"))
            connection.execute(text("INSERT INTO applications(job_id,notes) VALUES (1,'Keep me')"))
        migrate("head")
        with engine.begin() as connection:
            assert connection.scalar(text("SELECT user_id FROM saved_jobs")) == 1
            assert connection.scalar(text("SELECT notes FROM applications")) == "Keep me"
            assert connection.scalar(text("SELECT is_active FROM users WHERE id=1")) is False
            assert (
                connection.scalar(
                    text(
                        "INSERT INTO users(email,is_active,is_admin,profile,profile_version) "
                        "VALUES ('alice@example.com',true,false,'{}',1) RETURNING id"
                    )
                )
                == 2
            )
            connection.execute(text("INSERT INTO saved_jobs(user_id,job_id) VALUES (2,1)"))
            constraints = inspect(connection).get_unique_constraints("saved_jobs")
            assert any(row["column_names"] == ["user_id", "job_id"] for row in constraints)
        with engine.connect() as first, engine.connect() as second:
            assert first.scalar(text("SELECT pg_try_advisory_lock(728491632)")) is True
            try:
                assert second.scalar(text("SELECT pg_try_advisory_lock(728491632)")) is False
            finally:
                first.execute(text("SELECT pg_advisory_unlock(728491632)"))
        config = Settings(
            notifications_enabled=True,
            discord_webhook_url="https://example.invalid",
            telegram_bot_token="",
            telegram_chat_id="",
            match_keywords=[],
            match_sources=[],
            match_remote_only=False,
            match_min_salary=0,
        )
        with Session(engine) as db:
            rows = insert_new_jobs(
                db,
                [
                    {"title": "Engineer", "company": "Acme", "source": "Test", "url": url}
                    for url in ("https://example.invalid/1", "new-1", "new-2")
                ],
            )
            assert {row["url"] for row in rows} == {"new-1", "new-2"}
            enqueue(db, rows, config)
            db.commit()
            listing = discover(db, db.get(User, 2), page_size=1)
            assert listing["total"] == 3
            assert len(listing["items"]) == 1
        # Two independent workers skip each other's row locks, not their jobs.
        with Session(engine) as first, Session(engine) as second:
            locked = first.scalar(
                select(NotificationDelivery)
                .order_by(NotificationDelivery.id)
                .limit(1)
                .with_for_update()
            )
            assert locked is not None
            with patch("notifications.outbox.send_discord", return_value=1) as sender:
                assert drain(second, config)["discord"] == 1
                assert sender.call_count == 1
            first.rollback()
            with patch("notifications.outbox.send_discord", return_value=1) as sender:
                assert drain(second, config)["discord"] == 1
                assert sender.call_count == 1
    finally:
        engine.dispose()
        # Schema contains only objects created by this test; UUID is generated above.
        assert schema.startswith("jobhunter_verify_") and len(schema) == 49
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
