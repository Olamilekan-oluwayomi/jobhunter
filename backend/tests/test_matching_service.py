"""Tests for the matching service: scoring the DB, persistence and ranking.

Uses a fake session so the suite stays hermetic (no real database).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from database.models import Job
from matching.scorer import JobProfile
from matching.service import rank_jobs

PROFILE = JobProfile(
    roles=("Frontend Developer", "Frontend Engineer", "React Developer", "Software Engineer"),
    skills=(
        "React",
        "Next.js",
        "JavaScript",
        "TypeScript",
        "Tailwind CSS",
        "HTML",
        "CSS",
        "Supabase",
        "Git",
        "REST APIs",
    ),
    preferences=("Remote", "Junior / Entry-level", "Internship", "Full-time"),
)


def _job(id_: int, title: str, description: str = "", location: str = "Remote") -> Job:
    return Job(
        id=id_,
        title=title,
        company="Acme",
        location=location,
        description=description,
        url=f"https://example.com/{id_}",
        source="Remotive",
    )


def _fake_db(jobs: list[Job]) -> MagicMock:
    db = MagicMock()
    db.scalars.return_value.all.return_value = jobs
    return db


def test_rank_jobs_orders_by_score_desc():
    db = _fake_db(
        [
            _job(1, "Frontend Engineer", description="React, JavaScript, CSS."),
            _job(2, "Accountant", description="Excel only."),
        ]
    )
    result = rank_jobs(db, PROFILE, limit=10)
    assert result.total_scored == 2
    assert [item.job.id for item in result.items] == [1, 2]


def test_rank_jobs_filters_by_min_score():
    db = _fake_db(
        [
            _job(1, "Frontend Engineer", description="React, JavaScript, CSS."),
            _job(2, "React Developer", description="React only."),
        ]
    )
    result = rank_jobs(db, PROFILE, min_score=50, limit=10)
    assert [item.job.id for item in result.items] == [1]
    assert result.total_matched == 1


def test_rank_jobs_respects_limit():
    jobs = [_job(i, "Frontend Engineer", description=f"React job {i}.") for i in range(1, 6)]
    result = rank_jobs(db=_fake_db(jobs), profile=PROFILE, limit=3)
    assert len(result.items) == 3


def test_rank_jobs_persists_scores():
    db = _fake_db([_job(1, "Frontend Engineer", description="React.")])
    result = rank_jobs(db, PROFILE, limit=10)
    assert result.total_scored == 1
    db.execute.assert_called_once()
    db.commit.assert_called_once()
    args = db.execute.call_args
    rows = args[0][1] if len(args[0]) > 1 else None
    assert rows is not None
    assert rows[0]["job_id"] == 1
    assert rows[0]["score"] == result.items[0].score.score
    assert "React" in rows[0]["matched_skills"]


def test_rank_jobs_empty_database():
    result = rank_jobs(_fake_db([]), PROFILE, limit=10)
    assert result.total_scored == 0
    assert result.items == []
