"""High-level matching workflow: score every job and persist the results.

``rank_jobs`` loads all jobs, computes a deterministic score for each against
the given profile, upserts those scores into the ``job_scores`` table and
returns the best matches. Scores are recomputed and stored on every call so
the table always reflects the latest profile.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import repository as repo
from database.models import Job
from matching.scorer import JobProfile, JobScore, score_job


@dataclass(frozen=True)
class RankedJob:
    """A job together with its match score."""

    job: Job
    score: JobScore


@dataclass(frozen=True)
class RankingResult:
    items: list[RankedJob]
    total_scored: int
    total_matched: int


def build_score_row(job_id: int, score: JobScore) -> dict:
    """Serialize a ``JobScore`` into a row dict ready for persistence."""
    return {
        "job_id": job_id,
        "score": score.score,
        "role_points": score.role_points,
        "skill_points": score.skill_points,
        "preference_points": score.preference_points,
        "matched_roles": json.dumps(list(score.matched_roles)),
        "matched_skills": json.dumps(list(score.matched_skills)),
        "missing_skills": json.dumps(list(score.missing_skills)),
        "matched_preferences": json.dumps(list(score.matched_preferences)),
    }


def _job_dict(job: Job) -> dict:
    return {
        "title": job.title,
        "location": job.location,
        "description": job.description,
    }


def rank_jobs(
    db: Session,
    profile: JobProfile,
    *,
    min_score: int = 0,
    limit: int = 20,
) -> RankingResult:
    """Score every job in the database, persist the scores, and return the
    top ``limit`` jobs scoring at least ``min_score`` (highest first)."""
    jobs = list(db.scalars(select(Job)).all())

    rows: list[dict] = []
    scored: list[tuple[Job, JobScore]] = []
    for job in jobs:
        score = score_job(_job_dict(job), profile)
        rows.append(build_score_row(job.id, score))
        if score.score >= min_score:
            scored.append((job, score))

    repo.save_job_scores(db, rows)

    scored.sort(key=lambda pair: pair[1].score, reverse=True)
    items = [RankedJob(job=job, score=score) for job, score in scored[:limit]]
    return RankingResult(items=items, total_scored=len(jobs), total_matched=len(scored))
