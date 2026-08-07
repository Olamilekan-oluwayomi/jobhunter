from datetime import datetime, timezone

from sqlalchemy.orm import Session

from api.schemas import ScrapeResult
from scheduler.jobs import run_automation
from utils.logger import get_logger

logger = get_logger("api.scrape")


def run_scrape(db: Session) -> ScrapeResult:
    """Trigger the full automation (scrape → persist → notify).

    The `db` argument is accepted for API-route compatibility; the
    automation manages its own session.
    """
    report = run_automation(triggered_by="api")

    by_source = {source: stat["fetched"] for source, stat in report.by_source.items()}
    return ScrapeResult(
        started_at=report.started_at,
        completed_at=report.completed_at or datetime.now(timezone.utc),
        duration_seconds=report.duration_seconds,
        total_jobs=report.total_fetched,
        saved=report.new_jobs,
        already_exists=report.already_exists,
        by_source=by_source,
    )
