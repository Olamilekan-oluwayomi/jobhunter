from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import current_user
from api.dependencies import get_db
from api.schemas import SavedJobOut, SaveJobIn
from api.services import list_saved, save_job, unsave_job
from database.models import Application, SavedJob, User

router = APIRouter(tags=["saved"])


@router.get("/workspace-index")
def workspace_index(user: User = Depends(current_user), db: Session = Depends(get_db)):
    saved = (
        db.execute(select(SavedJob.id, SavedJob.job_id).where(SavedJob.user_id == user.id))
        .mappings()
        .all()
    )
    applications = (
        db.execute(
            select(Application.id, Application.job_id, Application.status).where(
                Application.user_id == user.id
            )
        )
        .mappings()
        .all()
    )
    return {
        "saved": [dict(row) for row in saved],
        "applications": [dict(row) for row in applications],
    }


@router.get(
    "/saved",
    response_model=list[SavedJobOut],
    summary="List saved jobs",
    description="Returns all saved jobs, most recently saved first.",
)
def saved_jobs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list_saved(db, user_id=user.id)


@router.post(
    "/save-job",
    response_model=SavedJobOut,
    status_code=status.HTTP_201_CREATED,
    summary="Save a job",
    description=(
        "Saves a job by id. Returns 404 when the job does not exist and 409 when "
        "it has already been saved."
    ),
    responses={
        404: {"description": "Job not found"},
        409: {"description": "Job already saved"},
    },
)
def save_a_job(
    payload: SaveJobIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    entry, error = save_job(db, payload, user_id=user.id)
    if error == "job not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "job already saved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return entry


@router.delete(
    "/save-job/{saved_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unsave a job",
    description="Removes a previously saved job by its saved-entry id. Returns 404 if not found.",
    responses={404: {"description": "Saved entry not found"}},
)
def unsave(saved_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    deleted = unsave_job(db, saved_id, user_id=user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved entry not found",
        )
