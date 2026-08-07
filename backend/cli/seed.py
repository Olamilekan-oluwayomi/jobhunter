"""Seed development data: sources, and sample applications/saved jobs.

Idempotent: safe to run repeatedly.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Application, Job, SavedJob, SessionLocal, Source
from utils.logger import get_logger

logger = get_logger("cli.seed")

DEV_SOURCES = [
    {"name": "Remotive", "url": "https://remotive.com"},
    {"name": "RemoteOK", "url": "https://remoteok.com"},
    {"name": "LinkedIn", "url": "https://linkedin.com/jobs"},
]


def seed_sources(db: Session) -> int:
    created = 0
    for data in DEV_SOURCES:
        exists = db.scalar(select(Source).where(Source.name == data["name"]))
        if exists is None:
            db.add(Source(**data))
            created += 1
    db.commit()
    return created


def seed_sample_relations(db: Session) -> tuple[int, int]:
    job = db.scalar(select(Job).order_by(Job.posted_at.desc()))
    if job is None:
        return 0, 0

    applications = 0
    saved = 0

    app_exists = db.scalar(select(Application).where(Application.job_id == job.id))
    if app_exists is None:
        db.add(
            Application(
                job_id=job.id,
                status="applied",
                notes="Seed application for development.",
            )
        )
        applications += 1

    saved_exists = db.scalar(select(SavedJob).where(SavedJob.job_id == job.id))
    if saved_exists is None:
        db.add(SavedJob(job_id=job.id))
        saved += 1

    db.commit()
    return applications, saved


def main() -> None:
    db: Session = SessionLocal()
    try:
        sources = seed_sources(db)
        applications, saved = seed_sample_relations(db)
    finally:
        db.close()

    logger.info(
        "Seeded %d source(s), %d application(s), %d saved job(s)",
        sources,
        applications,
        saved,
    )


if __name__ == "__main__":
    main()
