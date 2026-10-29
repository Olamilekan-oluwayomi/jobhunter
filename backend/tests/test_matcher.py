"""Tests for the job matcher rules."""

from __future__ import annotations

import pytest

from config import Settings
from notifications.matcher import job_matches, matches_any


def _settings(**overrides):
    base = {
        "match_keywords": [],
        "match_sources": [],
        "match_require_all_keywords": False,
        "match_remote_only": False,
        "match_min_salary": 0,
    }
    base.update(overrides)
    return Settings(**base)


def _job(**overrides) -> dict:
    job = {
        "title": "Senior Backend Engineer",
        "company": "Acme",
        "location": "Remote",
        "salary": "$150,000 - $180,000",
        "description": "Remote, Go, Postgres.",
        "source": "Remotive",
        "url": "https://example.com/job/1",
    }
    job.update(overrides)
    return job


def test_no_rules_matches_everything():
    assert matches_any(_job(), _settings()) is True


def test_keyword_any():
    assert matches_any(_job(), _settings(match_keywords=["go"])) is True


def test_keyword_missing():
    assert matches_any(_job(), _settings(match_keywords=["golang"])) is False


def test_keyword_all_required():
    want = _settings(
        match_keywords=["go", "remote"],
        match_require_all_keywords=True,
    )
    assert matches_any(_job(), want) is True

    half = _settings(
        match_keywords=["go", "kubernetes"],
        match_require_all_keywords=True,
    )
    assert matches_any(_job(), half) is False


def test_source_filter():
    blocked = _settings(match_sources=["Jobicy"])
    assert matches_any(_job(), blocked) is False


def test_remote_only():
    settings = _settings(match_remote_only=True)
    assert matches_any(_job(), settings) is True
    on_site = _job(location="On-site Lagos", description="Python, Django, APIs.")
    assert matches_any(on_site, settings) is False


def test_min_salary_annual():
    settings = _settings(match_min_salary=120_000)
    assert matches_any(_job(salary="$150,000 - $180,000"), settings) is True
    assert matches_any(_job(salary="$50,000"), settings) is False


def test_min_salary_hourly_converted_to_annual():
    settings = _settings(match_min_salary=80_000)
    # $60/hr * 40h * 52w = $124,800/yr.
    assert matches_any(_job(salary="$60 / hour"), settings) is True


def test_min_salary_without_salary_fails():
    settings = _settings(match_min_salary=100_000)
    assert matches_any(_job(salary=None), settings) is False


def test_job_matches_returns_decision():
    decision = job_matches(_job(), _settings())
    assert decision.matched is True
    assert decision.reasons == ()


@pytest.mark.parametrize(
    ("salary", "minimum", "expected"),
    [
        ("$100k-$150k", 100_000, True),
        ("$100k-$150k", 110_000, False),
        ("$5000 per month", 60_000, True),
        ("$5000 per month", 60_001, False),
        ("EUR 150000", 100_000, False),
        ("150000", 100_000, False),
    ],
)
def test_salary_threshold_uses_comparable_annual_lower_bound(salary, minimum, expected):
    assert matches_any(_job(salary=salary), _settings(match_min_salary=minimum)) is expected


@pytest.mark.parametrize("keyword", ["go", "React", "C++", "C#"])
def test_keywords_do_not_match_substrings_or_different_languages(keyword):
    job = _job(title="C developer", description="Django reactor", location="Lagos")
    assert not matches_any(job, _settings(match_keywords=[keyword]))


def test_notification_keywords_share_phrase_matching_with_scorer():
    job = _job(description="C++ and next-js development")
    assert matches_any(
        job, _settings(match_keywords=["C++", "Next.js"], match_require_all_keywords=True)
    )
