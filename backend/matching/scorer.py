"""Deterministic 0-100 job scoring against a candidate profile.

Scores are computed purely from keyword/phrase matches — no LLM. The three
components are weighted so they always sum to 100:

- role (30 points): the job title matches one of the profile's target roles
- skills (50 points): scaled by matched skills, reaching full credit once
  ``SKILL_FULL_AT`` profile skills are found (a job that lists the core
  stack is a strong match even if it omits a couple of niche skills)
- preferences (20 points): the share of profile preferences found in the text

Matching is case-insensitive and phrase-aware with word boundaries, so
"React" never matches "reactor" and "Full-time" matches "full time".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ROLE_WEIGHT = 30
SKILL_WEIGHT = 50
PREFERENCE_WEIGHT = 20
SKILL_FULL_AT = 5

TEXT_FIELDS = ("title", "location", "description")


@dataclass(frozen=True)
class JobProfile:
    """The candidate profile a job is matched against."""

    roles: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    preferences: tuple[str, ...] = ()


@dataclass(frozen=True)
class JobScore:
    """Breakdown of one job's match against a profile."""

    score: int
    role_points: int = 0
    skill_points: int = 0
    preference_points: int = 0
    matched_roles: tuple[str, ...] = ()
    matched_skills: tuple[str, ...] = ()
    missing_skills: tuple[str, ...] = ()
    matched_preferences: tuple[str, ...] = ()


def _clean(value: str | None) -> str:
    return (value or "").lower()


def _phrase_pattern(phrase: str) -> re.Pattern:
    """Word-boundary regex that tolerates whitespace, "-" or "." between tokens."""
    tokens = re.findall(r"[a-z0-9]+", phrase.lower())
    if not tokens:
        return re.compile(r"(?!)")
    return re.compile(r"\b" + r"[\s\-.]+".join(re.escape(t) for t in tokens) + r"\b")


def _job_text(job: dict) -> str:
    return " ".join(_clean(job.get(field)) for field in TEXT_FIELDS)


def score_job(job: dict, profile: JobProfile) -> JobScore:
    """Return the 0-100 match score of ``job`` against ``profile``."""
    title = _clean(job.get("title"))
    text = _job_text(job)

    roles = [(role, _phrase_pattern(role)) for role in profile.roles if role.strip()]
    skills = [(skill, _phrase_pattern(skill)) for skill in profile.skills if skill.strip()]
    preferences = [
        (pref, [_phrase_pattern(t) for t in pref.split("/") if t.strip()])
        for pref in profile.preferences
        if pref.strip()
    ]

    matched_roles = [role for role, pattern in roles if pattern.search(title)]
    matched_skills = [skill for skill, pattern in skills if pattern.search(text)]
    matched_preferences = [
        pref for pref, patterns in preferences if any(p.search(text) for p in patterns)
    ]

    role_points = ROLE_WEIGHT if matched_roles else 0
    skill_fraction = min(len(matched_skills) / SKILL_FULL_AT, 1.0) if profile.skills else 0.0
    skill_points = round(SKILL_WEIGHT * skill_fraction)
    preference_points = (
        round(PREFERENCE_WEIGHT * len(matched_preferences) / len(profile.preferences))
        if profile.preferences
        else 0
    )

    return JobScore(
        score=role_points + skill_points + preference_points,
        role_points=role_points,
        skill_points=skill_points,
        preference_points=preference_points,
        matched_roles=tuple(matched_roles),
        matched_skills=tuple(matched_skills),
        missing_skills=tuple(skill for skill in profile.skills if skill not in matched_skills),
        matched_preferences=tuple(matched_preferences),
    )
