from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import JobStats
from api.services import stats

router = APIRouter(tags=["stats"])


@router.get(
    "/stats",
    response_model=JobStats,
    summary="Aggregate statistics",
    description=(
        "Returns aggregate counters: total jobs, distinct sources, jobs grouped "
        "by source, applications grouped by status, and counts of saved jobs and "
        "total applications."
    ),
)
def stats_endpoint(db: Session = Depends(get_db)):
    return stats(db)
