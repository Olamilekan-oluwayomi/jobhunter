from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import SavedJobOut, SaveJobIn
from api.services import list_saved, save_job, unsave_job

router = APIRouter(tags=["saved"])


@router.get(
    "/saved",
    response_model=list[SavedJobOut],
    summary="List saved jobs",
    description="Returns all saved jobs, most recently saved first.",
)
def saved_jobs(db: Session = Depends(get_db)):
    return list_saved(db)


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
def save_a_job(payload: SaveJobIn, db: Session = Depends(get_db)):
    entry, error = save_job(db, payload)
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
def unsave(saved_id: int, db: Session = Depends(get_db)):
    deleted = unsave_job(db, saved_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved entry not found",
        )
