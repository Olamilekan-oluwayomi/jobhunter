from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import JobListOut, JobOut
from api.services import get_job, list_jobs

router = APIRouter(tags=["jobs"])


@router.get(
    "/jobs",
    response_model=JobListOut,
    summary="List jobs",
    description=(
        "Paginated list of jobs with optional search, filtering and sorting. "
        "Search matches title, company, location and description; filters narrow "
        "by source, company or location; sorting supports created_at, posted_at, "
        "title and company in ascending or descending order."
    ),
)
def jobs(
    page: int = Query(1, ge=1, description="Page number, 1-indexed."),
    page_size: int = Query(20, ge=1, le=1000, description="Items per page (1-1000)."),
    search: str | None = Query(
        None, max_length=200, description="Free-text search across job fields."
    ),
    source: str | None = Query(None, description="Exact source name filter."),
    company: str | None = Query(None, description="Company name substring filter."),
    location: str | None = Query(None, description="Location substring filter."),
    sort_by: str = Query(
        "posted_at",
        pattern="^(created_at|posted_at|title|company)$",
        description="Field to sort by.",
    ),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction."),
    db: Session = Depends(get_db),
):
    return list_jobs(
        db,
        page=page,
        page_size=page_size,
        search=search,
        source=source,
        company=company,
        location=location,
        sort_by=sort_by,
        order=order,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobOut,
    summary="Get a job",
    description="Fetch a single job by id. Returns 404 when the job does not exist.",
    responses={404: {"description": "Job not found"}},
)
def job_detail(job_id: int, db: Session = Depends(get_db)):
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
