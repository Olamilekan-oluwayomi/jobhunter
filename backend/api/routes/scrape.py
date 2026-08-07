from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import ScrapeResult
from api.services import run_scrape
from scheduler.jobs import list_recent_runs

router = APIRouter(tags=["scraping"])


@router.post(
    "/scrape",
    response_model=ScrapeResult,
    summary="Run the job scrape",
    description=(
        "Runs every configured scraper, normalizes the results, saves new jobs "
        "and reports how many were inserted versus already present, plus runtime."
    ),
)
def scrape(db: Session = Depends(get_db)):
    return run_scrape(db)


@router.get(
    "/scrape-runs",
    summary="Recent scrape executions",
    description=(
        "Returns the most recent automated scrape runs with per-source "
        "statistics and notification outcomes."
    ),
)
def scrape_runs(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    return list_recent_runs(limit=limit)
