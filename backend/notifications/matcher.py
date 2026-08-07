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
    """Lowest numeric value in the salary string, annualised, or None."""
    salary = job.get("salary") or ""
    if not salary:
        return None

    hourly = bool(re.search(r"(?:/\s*(?:hr|hour)|\bper\s*hour\b|hourly)", salary, re.IGNORECASE))
    numbers = [float(m) for m in re.findall(r"\d[\d,]*(?:\.\d+)?", salary.replace(",", ""))]
    if not numbers:
        return None

    lowest = min(numbers)
    if hourly:
        return lowest * 40 * 52
    return lowest


def job_matches(job: dict, settings: Settings) -> MatchDecision:
    keywords = [k for k in (settings.match_keywords or []) if k]

    if keywords:
        text = _job_text(job).lower()
        found = [k for k in keywords if k.lower() in text]
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
        if lo is None or lo < settings.match_min_salary:
            return MatchDecision(False, ("below minimum salary",))

    return MatchDecision(True)


def matches_any(job: dict, settings: Settings) -> bool:
    """Whether a job passes the configured matching rules."""
    return job_matches(job, settings).matched
