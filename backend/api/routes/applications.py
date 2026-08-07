from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate
from api.services import create_application, update_application

router = APIRouter(tags=["applications"])


@router.post(
    "/applications",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job application",
    description=(
        "Records an application for a job. Returns 404 when the job does not exist "
        "and 409 when an application for that job already exists."
    ),
    responses={
        404: {"description": "Job not found"},
        409: {"description": "Application already exists"},
    },
)
def create(payload: ApplicationCreate, db: Session = Depends(get_db)):
    entry, error = create_application(db, payload)
    if error == "job not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "application already exists for this job":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return entry


@router.patch(
    "/applications/{application_id}",
    response_model=ApplicationOut,
    summary="Update an application",
    description=(
        "Partially updates an application's status and/or notes. Returns 404 when "
        "the application does not exist."
    ),
    responses={404: {"description": "Application not found"}},
)
def update(
    application_id: int,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
):
    entry, error = update_application(db, application_id, payload)
    if error == "application not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    return entry
