from datetime import datetime

from pydantic import BaseModel


class ScrapeResult(BaseModel):
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    total_jobs: int
    saved: int
    already_exists: int
    by_source: dict[str, int] = {}
