"""Automated scrape cycle.

Executes every scraper, inserts only genuinely new jobs, records run
statistics and sends notifications for jobs matching the configured rules.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from config import get_settings
from database import SessionLocal
from database.repository import create_scrape_run, insert_new_jobs
from notifications.outbox import drain, enqueue
from scheduler.lock import scrape_lock
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
    with scrape_lock():
        return _run_automation(triggered_by)


def _run_automation(triggered_by: str) -> RunReport:
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

        # Insert exact conflict winners and queue notifications in the same transaction.
        for source, jobs in by_source_jobs.items():
            inserted_jobs = insert_new_jobs(db, jobs)
            enqueue(db, inserted_jobs)
            db.commit()
            inserted = len(inserted_jobs)
            exists = len(jobs) - inserted
            by_source[source] = {"fetched": len(jobs), "new": inserted, "exists": exists}
            already += exists
            new_jobs.extend(inserted_jobs)

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

        settings = get_settings()
        delivered = drain(db, settings)
        notified = {
            "discord": delivered["discord"],
            "telegram": delivered["telegram"],
            "failed": delivered["failed"],
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
