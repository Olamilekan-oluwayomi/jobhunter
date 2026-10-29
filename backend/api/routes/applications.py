from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.auth import current_user
from api.dependencies import get_db
from api.schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate
from api.schemas.application import ApplicationListOut, ApplicationStatus
from api.services import create_application, update_application
from database import repository as repo
from database.models import User

router = APIRouter(tags=["applications"])


@router.get("/applications", response_model=ApplicationListOut, summary="List applications")
def list_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    application_status: ApplicationStatus | None = Query(None, alias="status"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    entries, total = repo.list_applications(
        db, page=page, page_size=page_size, status=application_status, user_id=user.id
    )
    return ApplicationListOut(
        items=[ApplicationOut.model_validate(entry) for entry in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


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
def create(
    payload: ApplicationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    entry, error = create_application(db, payload, user_id=user.id)
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
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    entry, error = update_application(db, application_id, payload, user_id=user.id)
    if error == "application not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    return entry
