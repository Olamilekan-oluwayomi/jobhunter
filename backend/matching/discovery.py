"""Shared metadata and cached, server-paginated account discovery."""

import json
import re
from dataclasses import asdict

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from database.models import CandidateScore, Job, SavedJob
from matching.scorer import JobProfile, phrase_pattern, score_job


def job_metadata(job, profile):
    text = f"{job.title} {job.description or ''}"
    employment_type = (
        "Contract"
        if re.search(r"\bcontract\b", text, re.IGNORECASE)
        else (
            "Full-time" if re.search(r"\bfull[- ]time\b", text, re.IGNORECASE) else "Not specified"
        )
    )
    level = (
        "Senior"
        if re.search(r"\b(senior|staff|lead|principal)\b", job.title, re.IGNORECASE)
        else (
            "Junior"
            if re.search(r"\b(junior|intern|entry)\b", job.title, re.IGNORECASE)
            else "Not specified"
        )
    )
    location = job.location or ""
    country = profile.get("location", "").strip()
    eligible = "unknown"
    detail = "Confirm country and work authorization requirements with the employer."
    # Infer only from the source location field and preserve the evidence.
    if re.search(r"\b(not|except|excluding|must|only|restricted)\b", location, re.IGNORECASE):
        if (
            country
            and phrase_pattern(country).search(location)
            and not re.search(r"\b(not|except|excluding)\b", location, re.IGNORECASE)
        ):
            eligible = "eligible"
    elif (
        re.search(r"\b(worldwide|anywhere in the world)\b", location, re.IGNORECASE)
        or (country and phrase_pattern(country).search(location))
        or (
            country.lower() in {"nigeria", "ghana", "kenya", "south africa"}
            and re.search(r"\bafrica\b", location, re.IGNORECASE)
        )
    ):
        eligible = "eligible"
    restrictions = {
        "United States": r"\b(?:US|USA|United States)\s*(?:only|residents)\b",
        "United Kingdom": r"\b(?:UK|United Kingdom)\s*(?:only|residents)\b",
        "Canada": r"\bCanada\s*(?:only|residents)\b",
    }
    for required, pattern in restrictions.items():
        if re.search(pattern, location, re.IGNORECASE) and not re.search(
            r"\b(not|except|excluding)\b", location, re.IGNORECASE
        ):
            eligible = "eligible" if country.casefold() == required.casefold() else "restricted"
    if eligible != "unknown":
        detail = f'Source location: "{location}". Work authorization still needs checking.'
    return {
        "type": employment_type,
        "level": level,
        "eligibility": {"status": eligible, "detail": detail},
    }


def candidate_profile(profile):
    return JobProfile(
        roles=(profile.get("role", ""),),
        skills=tuple(profile.get("skills", [])),
        preferences=("Remote",) if profile.get("remote") else (),
    )


def job_details(job, profile):
    score = score_job(
        {"title": job.title, "description": job.description, "location": job.location},
        candidate_profile(profile),
    )
    return {**job_metadata(job, profile), "match": asdict(score)}


def refresh_scores(db, user):
    """Score only new/changed jobs or a changed profile, in bounded batches."""
    profile = json.loads(user.profile)
    # Serialize cache refreshes per user on PostgreSQL, including profile updates.
    # SQLite tests serialize through their single connection.
    if db.get_bind().dialect.name == "postgresql":
        from database.models import User

        db.execute(select(User.id).where(User.id == user.id).with_for_update())
        db.refresh(user)
        profile = json.loads(user.profile)
    join = and_(CandidateScore.job_id == Job.id, CandidateScore.user_id == user.id)
    stale = or_(
        CandidateScore.id.is_(None),
        CandidateScore.profile_version != user.profile_version,
        CandidateScore.job_updated_at < Job.updated_at,
    )
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    while True:
        jobs = list(
            db.scalars(
                select(Job).outerjoin(CandidateScore, join).where(stale).order_by(Job.id).limit(200)
            ).all()
        )
        if not jobs:
            break
        rows = []
        for job in jobs:
            details = job_details(job, profile)
            rows.append(
                {
                    "user_id": user.id,
                    "job_id": job.id,
                    "profile_version": user.profile_version,
                    "job_updated_at": job.updated_at,
                    "score": details["match"]["score"],
                    "details": json.dumps(details),
                    "eligibility": details["eligibility"]["status"],
                    "employment_type": details["type"],
                }
            )
        statement = insert(CandidateScore)
        db.execute(
            statement.on_conflict_do_update(
                index_elements=[CandidateScore.user_id, CandidateScore.job_id],
                set_={
                    key: getattr(statement.excluded, key)
                    for key in rows[0]
                    if key not in {"user_id", "job_id"}
                },
            ),
            rows,
        )
    db.commit()


def discover(
    db,
    user,
    *,
    page=1,
    page_size=20,
    search=None,
    employment_type=None,
    eligible_only=False,
    saved_only=False,
    sort="match",
):
    refresh_scores(db, user)
    conditions = [CandidateScore.user_id == user.id]
    if search:
        # Search is literal; user wildcard characters must not expand the result set.
        pattern = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conditions.append(
            or_(
                *(
                    column.ilike(pattern, escape="\\")
                    for column in (Job.title, Job.company, Job.description, Job.location)
                )
            )
        )
    if employment_type:
        conditions.append(CandidateScore.employment_type == employment_type)
    if eligible_only:
        conditions.append(CandidateScore.eligibility == "eligible")
    if saved_only:
        conditions.append(
            exists(
                select(SavedJob.id).where(SavedJob.job_id == Job.id, SavedJob.user_id == user.id)
            )
        )
    base = (
        select(Job, CandidateScore)
        .join(CandidateScore, CandidateScore.job_id == Job.id)
        .where(*conditions)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    ordering = (
        (Job.posted_at.desc().nullslast(), Job.id.desc())
        if sort == "newest"
        else (CandidateScore.score.desc(), Job.posted_at.desc().nullslast(), Job.id.desc())
    )
    rows = db.execute(
        base.order_by(*ordering).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [present(job, score) for job, score in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def present(job, score=None, *, profile=None, include_description=False):
    details = json.loads(score.details) if score else job_details(job, profile or {})
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary": job.salary,
        "url": job.url,
        "source": job.source,
        "posted_at": job.posted_at,
        "created_at": job.created_at,
        "description": job.description if include_description else None,
        **details,
    }
