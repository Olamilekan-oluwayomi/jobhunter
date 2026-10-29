import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.auth import current_user
from api.dependencies import get_db
from database.models import Job, User
from matching.discovery import discover, present

router = APIRouter(tags=["discovery"])


@router.get("/discovery")
def discovery(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    employment_type: Literal["Contract", "Full-time"] | None = None,
    eligible_only: bool = False,
    saved_only: bool = False,
    sort: Literal["match", "newest"] = "match",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return discover(
        db,
        user,
        page=page,
        page_size=page_size,
        search=search,
        employment_type=employment_type,
        eligible_only=eligible_only,
        saved_only=saved_only,
        sort=sort,
    )


@router.get("/discovery/{job_id}")
def detail(job_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return present(job, profile=json.loads(user.profile), include_description=True)
