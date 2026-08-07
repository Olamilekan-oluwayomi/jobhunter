from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload

from .models import Application, Job, JobScore, SavedJob, ScrapeRun, Source

JOB_SEARCH_COLUMNS = (Job.title, Job.company, Job.location, Job.description)

#: Workflow statuses a job can be in. "saved" lives in the saved_jobs table;
#: the rest are application statuses.
WORKFLOW_STATUSES = ("saved", "applied", "interview", "rejected", "offer")


def save_job_scores(db: Session, rows: list[dict]) -> None:
    """Upsert match-score rows for many jobs in a single transaction.

    Uses PostgreSQL ``ON CONFLICT (job_id) DO UPDATE`` so re-scoring after a
    profile change refreshes existing rows instead of duplicating them.
    """
    if not rows:
        return

    excluded = insert(JobScore).excluded
    stmt = insert(JobScore).on_conflict_do_update(
        index_elements=[JobScore.job_id],
        set_={
            "score": excluded.score,
            "role_points": excluded.role_points,
            "skill_points": excluded.skill_points,
            "preference_points": excluded.preference_points,
            "matched_roles": excluded.matched_roles,
            "matched_skills": excluded.matched_skills,
            "missing_skills": excluded.missing_skills,
            "matched_preferences": excluded.matched_preferences,
            "updated_at": func.now(),
        },
    )
    db.execute(stmt, rows)
    db.commit()


def _ensure_source(db: Session, name: str) -> Source:
    source = db.scalar(select(Source).where(Source.name == name))
    if source is None:
        source = Source(name=name)
        db.add(source)
        db.flush()
    return source


def save_job(db: Session, job: dict) -> bool:
    _ensure_source(db, job["source"])
    stmt = insert(Job).values(**job).on_conflict_do_nothing(index_elements=[Job.url])
    result = db.execute(stmt)
    db.commit()
    return result.rowcount > 0


def save_jobs_bulk(db: Session, jobs: list[dict]) -> int:
    """Insert many new jobs in a single transaction.

    Uses PostgreSQL ``ON CONFLICT DO NOTHING`` on the url unique key so only
    genuinely new rows are inserted. Commits once instead of per row. Returns
    the number of rows actually inserted.
    """
    if not jobs:
        return 0

    seen_urls: set[str] = set()
    rows: list[dict] = []
    for job in jobs:
        url = job["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        _ensure_source(db, job["source"])
        rows.append(job)

    if not rows:
        return 0

    stmt = insert(Job).on_conflict_do_nothing(index_elements=[Job.url])
    result = db.execute(stmt, rows)
    db.commit()
    return max(result.rowcount or 0, 0)


def _job_status_condition(status: str):
    """SQL predicate for a workflow status filter.

    ``saved`` means the job has a saved_jobs entry and no application yet;
    the other statuses match the application record's status. The five
    statuses are mutually exclusive, so a saved-then-applied job only shows
    up under its application status.
    """
    if status == "saved":
        return and_(
            exists(select(SavedJob.id).where(SavedJob.job_id == Job.id)),
            ~exists(select(Application.id).where(Application.job_id == Job.id)),
        )
    return exists(
        select(Application.id).where(
            Application.job_id == Job.id,
            Application.status == status,
        )
    )


def _job_filters(
    search: str | None,
    source: str | None,
    company: str | None,
    location: str | None,
    status: str | None = None,
):
    conditions = []
    if search:
        pattern = f"%{search}%"
        conditions.append(or_(*[col.ilike(pattern) for col in JOB_SEARCH_COLUMNS]))
    if source:
        conditions.append(Job.source == source)
    if company:
        conditions.append(Job.company.ilike(f"%{company}%"))
    if location:
        conditions.append(Job.location.ilike(f"%{location}%"))
    if status:
        conditions.append(_job_status_condition(status))
    return conditions


def list_jobs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    source: str | None = None,
    company: str | None = None,
    location: str | None = None,
    status: str | None = None,
    sort_by: str = "posted_at",
    order: str = "desc",
) -> tuple[list[Job], int]:
    conditions = _job_filters(search, source, company, location, status)
    where = and_(*conditions) if conditions else None

    count_stmt = select(func.count(Job.id))
    if where is not None:
        count_stmt = count_stmt.where(where)
    total = db.scalar(count_stmt)

    column = {
        "posted_at": Job.posted_at,
        "created_at": Job.created_at,
        "title": Job.title,
        "company": Job.company,
    }.get(sort_by, Job.posted_at)

    ordering = column.desc() if order == "desc" else column.asc()
    stmt = select(Job)
    if where is not None:
        stmt = stmt.where(where)
    stmt = stmt.order_by(ordering, Job.id.desc()).offset((page - 1) * page_size).limit(page_size)
    jobs = db.scalars(stmt).all()
    return list(jobs), total


def get_job(db: Session, job_id: int) -> Job | None:
    return db.get(Job, job_id)


def list_sources(db: Session) -> list[Source]:
    job_counts = (
        select(Job.source, func.count(Job.id).label("job_count")).group_by(Job.source).subquery()
    )
    stmt = (
        select(Source, func.coalesce(job_counts.c.job_count, 0).label("job_count"))
        .outerjoin(job_counts, Source.name == job_counts.c.source)
        .order_by(Source.name)
    )
    return db.execute(stmt).all()


def list_saved_jobs(db: Session) -> list[SavedJob]:
    stmt = (
        select(SavedJob)
        .options(
            joinedload(SavedJob.job).joinedload(Job.match_score),
            joinedload(SavedJob.job).joinedload(Job.applications),
        )
        .order_by(SavedJob.saved_at.desc())
    )
    return list(db.scalars(stmt).unique().all())


def get_saved_job(db: Session, saved_id: int) -> SavedJob | None:
    return db.get(SavedJob, saved_id)


def create_saved_job(db: Session, job_id: int) -> SavedJob | None:
    if db.scalar(select(SavedJob).where(SavedJob.job_id == job_id)):
        return None
    entry = SavedJob(job_id=job_id)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def delete_saved_job(db: Session, saved_id: int) -> bool:
    entry = db.get(SavedJob, saved_id)
    if entry is None:
        return False
    db.delete(entry)
    db.commit()
    return True


def purge_orphaned_saved(db: Session) -> int:
    orphaned = db.query(SavedJob).filter(SavedJob.job_id.notin_(select(Job.id))).all()
    count = len(orphaned)
    for entry in orphaned:
        db.delete(entry)
    db.commit()
    return count


def purge_orphaned_applications(db: Session) -> int:
    orphaned = db.query(Application).filter(Application.job_id.notin_(select(Job.id))).all()
    count = len(orphaned)
    for entry in orphaned:
        db.delete(entry)
    db.commit()
    return count


def purge_all_data(db: Session) -> dict:
    saved = db.query(SavedJob).delete()
    apps = db.query(Application).delete()
    jobs = db.query(Job).delete()
    db.commit()
    return {"saved": saved, "applications": apps, "jobs": jobs}


def get_application(db: Session, application_id: int) -> Application | None:
    return db.scalar(
        select(Application)
        .options(joinedload(Application.job))
        .where(Application.id == application_id)
    )


def create_application(
    db: Session,
    job_id: int,
    status: str,
    notes: str | None,
) -> Application | None:
    if db.scalar(select(Application).where(Application.job_id == job_id)):
        return None
    entry = Application(job_id=job_id, status=status, notes=notes)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def upsert_application(
    db: Session,
    job_id: int,
    status: str,
    notes: str | None = None,
) -> Application:
    """Create an application for a job, or update the existing one.

    Idempotent: a job can have at most one application record. Re-applying
    sets the status (and notes when provided) while preserving the original
    ``applied_at`` so the first application date is never lost.
    """
    existing = db.scalar(select(Application).where(Application.job_id == job_id))
    if existing is not None:
        existing.status = status
        if notes is not None:
            existing.notes = notes
        db.commit()
        db.refresh(existing)
        return existing
    entry = Application(job_id=job_id, status=status, notes=notes)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def update_application(
    db: Session,
    application: Application,
    *,
    status: str | None = None,
    notes: str | None = None,
) -> Application:
    if status is not None:
        application.status = status
    if notes is not None:
        application.notes = notes
    db.commit()
    db.refresh(application)
    return application


def create_scrape_run(db: Session, run: dict) -> ScrapeRun:
    entry = ScrapeRun(**run)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def latest_scrape_runs(db: Session, limit: int = 10) -> list[ScrapeRun]:
    stmt = select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def get_stats(db: Session) -> dict:
    total_jobs = db.scalar(select(func.count(Job.id)))
    sources = db.scalar(select(func.count(func.distinct(Job.source))))
    by_source = dict(db.execute(select(Job.source, func.count(Job.id)).group_by(Job.source)).all())
    by_status = dict(
        db.execute(
            select(Application.status, func.count(Application.id)).group_by(Application.status)
        ).all()
    )
    total_saved = db.scalar(select(func.count(SavedJob.id)))
    total_applications = db.scalar(select(func.count(Application.id)))
    return {
        "total_jobs": total_jobs,
        "sources": sources,
        "by_source": by_source,
        "by_status": by_status,
        "total_saved": total_saved,
        "total_applications": total_applications,
    }
