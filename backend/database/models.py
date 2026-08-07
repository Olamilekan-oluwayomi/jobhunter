from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)

    jobs: Mapped[list["Job"]] = relationship(back_populates="source_ref")


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("url"),
        CheckConstraint(
            "length(title) > 0",
            name="title_not_empty",
        ),
        CheckConstraint(
            "length(company) > 0",
            name="company_not_empty",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    location: Mapped[str | None] = mapped_column(Text)
    salary: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        Text,
        ForeignKey("sources.name", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    source_ref: Mapped["Source"] = relationship(back_populates="jobs")
    match_score: Mapped["JobScore | None"] = relationship(
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    saved_entries: Mapped[list["SavedJob"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('applied', 'interview', 'offer', 'rejected')",
            name="valid_status",
        ),
        UniqueConstraint("job_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, server_default="applied", index=True, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)

    job: Mapped["Job"] = relationship(back_populates="applications")


class SavedJob(Base, TimestampMixin):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("job_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    saved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    job: Mapped["Job"] = relationship(back_populates="saved_entries")


class JobScore(Base, TimestampMixin):
    """A persisted deterministic match score for one job."""

    __tablename__ = "job_scores"
    __table_args__ = (
        UniqueConstraint("job_id"),
        CheckConstraint("score >= 0 AND score <= 100", name="score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    role_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skill_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    preference_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_roles: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    matched_skills: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    missing_skills: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    matched_preferences: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    job: Mapped["Job"] = relationship(back_populates="match_score")


class ScrapeRun(Base, TimestampMixin):
    """A single automated scraping run with per-source statistics."""

    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    triggered_by: Mapped[str] = mapped_column(Text, server_default="scheduler", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_seconds: Mapped[float | None] = mapped_column()
    total_fetched: Mapped[int] = mapped_column(default=0, nullable=False)
    new_jobs: Mapped[int] = mapped_column(default=0, nullable=False)
    already_exists: Mapped[int] = mapped_column(default=0, nullable=False)
    succeeded: Mapped[int] = mapped_column(default=0, nullable=False)
    failed: Mapped[str] = mapped_column(Text, default="")
    by_source: Mapped[str] = mapped_column(
        Text, default="{}", nullable=False
    )  # JSON: source -> {fetched, new, exists}
    by_source_failed: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    notified: Mapped[str] = mapped_column(
        Text, default="{}", nullable=False
    )  # JSON: matched?, notify summary
