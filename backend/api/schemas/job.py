from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class JobOut(BaseModel):
    id: int
    title: str
    company: str
    location: str | None = None
    salary: str | None = None
    description: str | None = None
    url: str
    source: str
    posted_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class JobSearchParams(BaseModel):
    """Query parameters accepted by GET /jobs."""

    search: str | None = Field(
        None,
        max_length=200,
        description="Case-insensitive term matched against title, company and description.",
    )
    source: str | None = Field(None, description="Filter by exact source name.")
    location: str | None = Field(
        None, description="Filter by location substring (case-insensitive)."
    )
    sort_by: Literal["posted_at", "created_at", "title", "company"] = "posted_at"
    order: Literal["asc", "desc"] = "desc"


class JobListOut(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    page_size: int


class JobStats(BaseModel):
    total_jobs: int
    sources: int
    by_source: dict[str, int] = {}
    by_status: dict[str, int] = {}
    total_saved: int = 0
    total_applications: int = 0
