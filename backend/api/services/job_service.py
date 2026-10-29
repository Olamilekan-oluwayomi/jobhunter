from sqlalchemy.orm import Session

from api.schemas import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
    JobListOut,
    JobOut,
    JobStats,
    SavedJobOut,
    SaveJobIn,
    SourceOut,
)
from database import repository as repo


def list_jobs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    source: str | None = None,
    company: str | None = None,
    location: str | None = None,
    sort_by: str = "posted_at",
    order: str = "desc",
) -> JobListOut:
    jobs, total = repo.list_jobs(
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
    return JobListOut(
        items=[JobOut.model_validate(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_job(db: Session, job_id: int) -> JobOut | None:
    job = repo.get_job(db, job_id)
    return JobOut.model_validate(job) if job else None


def stats(db: Session, user_id: int = 1) -> JobStats:
    return JobStats(**repo.get_stats(db, user_id=user_id))


def list_sources(db: Session) -> list[SourceOut]:
    rows = repo.list_sources(db)
    return [
        SourceOut(
            id=source.id,
            name=source.name,
            url=source.url,
            job_count=count,
        )
        for source, count in rows
    ]


def list_saved(db: Session, user_id: int = 1) -> list[SavedJobOut]:
    entries = repo.list_saved_jobs(db, user_id=user_id)
    return [SavedJobOut.model_validate(entry) for entry in entries]


def save_job(
    db: Session, payload: SaveJobIn, user_id: int = 1
) -> tuple[SavedJobOut | None, str | None]:
    job = repo.get_job(db, payload.job_id)
    if job is None:
        return None, "job not found"
    entry = repo.create_saved_job(db, payload.job_id, user_id=user_id)
    if entry is None:
        return None, "job already saved"
    return SavedJobOut.model_validate(entry), None


def unsave_job(db: Session, saved_id: int, user_id: int = 1) -> bool:
    return repo.delete_saved_job(db, saved_id, user_id=user_id)


def create_application(
    db: Session, payload: ApplicationCreate, user_id: int = 1
) -> tuple[ApplicationOut | None, str | None]:
    job = repo.get_job(db, payload.job_id)
    if job is None:
        return None, "job not found"
    entry = repo.create_application(
        db, payload.job_id, payload.status, payload.notes, user_id=user_id
    )
    if entry is None:
        return None, "application already exists for this job"
    return ApplicationOut.model_validate(entry), None


def update_application(
    db: Session, application_id: int, payload: ApplicationUpdate, user_id: int = 1
) -> tuple[ApplicationOut | None, str | None]:
    entry = repo.get_application(db, application_id, user_id=user_id)
    if entry is None:
        return None, "application not found"
    updated = repo.update_application(
        db,
        entry,
        **payload.model_dump(exclude_unset=True),
    )
    return ApplicationOut.model_validate(updated), None
