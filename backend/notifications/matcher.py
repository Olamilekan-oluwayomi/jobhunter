"""Job matching rules used to decide which notifications get sent.

A matched job satisfies all configured constraints:
- text fields contain every required keyword (or any when require_all is False)
- its source is one of the allowed sources (when configured)
- it is remote (when remote-only matching is on)
- its parsed salary meets the configured minimum (when configured)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from config import Settings
from matching.salary import parse_salary
from matching.scorer import phrase_pattern

_TEXT_FIELDS = ("title", "company", "location", "salary", "description")


@dataclass(frozen=True)
class MatchDecision:
    matched: bool
    reasons: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return self.matched


def _job_text(job: dict) -> str:
    return " ".join(str(job.get(f, "") or "") for f in _TEXT_FIELDS)


def _mentions_remote(job: dict) -> bool:
    return bool(re.search(r"\bremote\b", _job_text(job), re.IGNORECASE))


def _annual_salary_min(job: dict) -> float | None:
    """Annualized USD lower bound, or None when it cannot be compared."""
    salary = parse_salary(job.get("salary"))
    return salary.annual_minimum if salary else None


def job_matches(job: dict, settings: Settings) -> MatchDecision:
    keywords = [k.strip() for k in (settings.match_keywords or []) if k.strip()]

    if keywords:
        text = _job_text(job).lower()
        found = [k for k in keywords if phrase_pattern(k).search(text)]
        if settings.match_require_all_keywords and len(found) != len(keywords):
            return MatchDecision(False, ("missing required keywords",))
        if not settings.match_require_all_keywords and not found:
            return MatchDecision(False, ("no keyword matched",))

    if settings.match_sources and job.get("source") not in settings.match_sources:
        return MatchDecision(False, (f"source not wanted: {job.get('source')}",))

    if settings.match_remote_only and not _mentions_remote(job):
        return MatchDecision(False, ("not remote",))

    if settings.match_min_salary:
        lo = _annual_salary_min(job)
        if lo is None:
            return MatchDecision(False, ("salary unavailable or not comparable in USD",))
        if lo < settings.match_min_salary:
            return MatchDecision(False, ("below minimum salary",))

    return MatchDecision(True)


def matches_any(job: dict, settings: Settings) -> bool:
    """Whether a job passes the configured matching rules."""
    return job_matches(job, settings).matched
