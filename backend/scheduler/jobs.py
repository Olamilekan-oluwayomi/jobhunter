"""Automated scrape cycle.

Executes every scraper, inserts only genuinely new jobs, records run
statistics and sends notifications for jobs matching the configured rules.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

import sqlalchemy as _sa

from config import get_settings
from database import SessionLocal
from database.models import Job
from database.repository import create_scrape_run, save_jobs_bulk
from notifications.service import notify_new_jobs
from scrapers.manager import ScraperManager
from utils.logger import get_logger

logger = get_logger("scheduler.jobs")


@dataclass(frozen=True)
class RunReport:
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float
    total_fetched: int
    new_jobs: int
    already_exists: int
    by_source: dict[str, dict] = field(default_factory=dict)
    notified: dict = field(default_factory=dict)
    succeeded_sources: int = 0
    failed_sources: list[str] = field(default_factory=list)
    by_source_failed: dict[str, str] = field(default_factory=dict)


def run_automation(triggered_by: str = "scheduler") -> RunReport:
    """Fetch jobs from every scraper, persist only the new ones, log
    per-source statistics, then notify about matched jobs."""
    started_at = datetime.now(timezone.utc)
    manager = ScraperManager()
    fetched = manager.fetch_all()
    results = manager.results

    db = SessionLocal()
    try:
        new_jobs: list[dict] = []
        already = 0
        by_source: dict[str, dict] = {}

        by_source_jobs: dict[str, list[dict]] = {}
        for job in fetched:
            source = job.get("source") or "unknown"
            by_source_jobs.setdefault(source, []).append(job)

        # Bulk-insert per source in a single transaction each; speed ~100x
        # faster than one INSERT+COMMIT per job for large fetches. Determine
        # which URLs already exist up front so we can attribute notifications
        # to genuinely new rows.
        for source, jobs in by_source_jobs.items():
            urls = {job["url"] for job in jobs}
            existing = set(db.scalars(_sa.select(Job.url).where(Job.url.in_(urls))).all())
            fresh = [job for job in jobs if job["url"] not in existing]

            inserted = save_jobs_bulk(db, fresh)
            exists = len(jobs) - inserted
            by_source[source] = {
                "fetched": len(jobs),
                "new": inserted,
                "exists": exists,
            }
            already += exists
            new_jobs.extend(fresh[:inserted])

        for source, result in results.items():
            entry = by_source.setdefault(source, {"fetched": result.parsed, "new": 0, "exists": 0})
            entry["status"] = result.status

        failed_sources = [
            source for source, result in results.items() if result.status not in ("OK", "DISABLED")
        ]
        by_source_failed = {
            source: result.message or result.status
            for source, result in results.items()
            if result.status not in ("OK", "DISABLED")
        }
        succeeded_sources = sum(1 for result in results.values() if result.status == "OK")

        notify = notify_new_jobs(new_jobs)
        settings = get_settings()
        notified = {
            "matched": notify.matched,
            "discord": notify.discord_sent,
            "telegram": notify.telegram_sent,
            "channels_enabled": settings.any_channel_enabled,
        }

        completed_at = datetime.now(timezone.utc)
        report = RunReport(
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=(completed_at - started_at).total_seconds(),
            total_fetched=len(fetched),
            new_jobs=len(new_jobs),
            already_exists=already,
            by_source=by_source,
            notified=notified,
            succeeded_sources=succeeded_sources,
            failed_sources=failed_sources,
            by_source_failed=by_source_failed,
        )

        _persist_run(db, triggered_by, report)

        logger.info(
            "automation complete: fetched=%s new=%s exists=%s matched=%s in %.2fs",
            report.total_fetched,
            report.new_jobs,
            report.already_exists,
            notified.get("matched", 0),
            report.duration_seconds,
        )
        return report
    finally:
        db.close()


def list_recent_runs(limit: int = 10) -> list[dict]:
    """Return the most recent persisted run summaries (for CLI/API display)."""
    from database.repository import latest_scrape_runs

    db = SessionLocal()
    try:
        runs = latest_scrape_runs(db, limit=limit)
    finally:
        db.close()

    return [
        {
            "id": run.id,
            "triggered_by": run.triggered_by,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "duration_seconds": run.duration_seconds,
            "total_fetched": run.total_fetched,
            "new_jobs": run.new_jobs,
            "already_exists": run.already_exists,
            "by_source": _safe_json(run.by_source),
            "by_source_failed": _safe_json(run.by_source_failed),
            "notified": _safe_json(run.notified),
        }
        for run in runs
    ]


def _safe_json(value: str) -> dict:
    try:
        return json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}


def _persist_run(db, triggered_by: str, report: RunReport) -> None:
    create_scrape_run(
        db,
        {
            "triggered_by": triggered_by,
            "started_at": report.started_at.replace(tzinfo=None),
            "completed_at": (
                report.completed_at.replace(tzinfo=None) if report.completed_at else None
            ),
            "duration_seconds": report.duration_seconds,
            "total_fetched": report.total_fetched,
            "new_jobs": report.new_jobs,
            "already_exists": report.already_exists,
            "succeeded": report.succeeded_sources,
            "failed": json.dumps(report.failed_sources),
            "by_source": json.dumps(report.by_source, default=str),
            "by_source_failed": json.dumps(report.by_source_failed, default=str),
            "notified": json.dumps(report.notified, default=str),
        },
    )
