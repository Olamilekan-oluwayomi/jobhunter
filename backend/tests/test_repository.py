"""Tests for the repository's bulk-insert path.

The insert helper targets PostgreSQL, so we assert semantics against a fake
session rather than spinning up a database.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from database.repository import save_job_scores, save_jobs_bulk


def _job(url: str, source: str = "Remotive") -> dict:
    return {
        "title": "Backend Engineer",
        "company": "Acme",
        "location": "Remote",
        "salary": None,
        "description": "Go + Postgres.",
        "url": url,
        "source": source,
        "posted_at": None,
    }


def test_empty_list_is_a_noop():
    db = MagicMock()
    assert save_jobs_bulk(db, []) == 0
    db.execute.assert_not_called()


def test_deduplicates_urls_within_batch():
    db = MagicMock()
    db.execute.return_value.rowcount = 1
    jobs = [_job("u1"), _job("u1")]
    assert save_jobs_bulk(db, jobs) == 1
    # One row kept; only a single execute/commit happened.
    db.execute.assert_called_once()
    db.commit.assert_called_once()


def test_commits_once_for_many_rows():
    db = MagicMock()
    db.execute.return_value.rowcount = 3
    jobs = [_job(f"u{i}") for i in range(3)]
    assert save_jobs_bulk(db, jobs) == 3
    db.execute.assert_called_once()
    db.commit.assert_called_once()


def test_ensures_sources_exist_before_insert():
    db = MagicMock()
    db.scalar.return_value = None  # no existing Source
    db.execute.return_value.rowcount = 1
    save_jobs_bulk(db, [_job("u1", source="Jobicy")])
    assert db.add.call_count == 1
    db.flush.assert_called_once()


def test_rowcount_handled_when_none():
    db = MagicMock()
    db.execute.return_value.rowcount = None
    assert save_jobs_bulk(db, [_job("u1")]) == 0


def _score_row(job_id: int = 1) -> dict:
    return {
        "job_id": job_id,
        "score": 80,
        "role_points": 30,
        "skill_points": 35,
        "preference_points": 15,
        "matched_roles": '["Frontend Engineer"]',
        "matched_skills": '["React"]',
        "missing_skills": "[]",
        "matched_preferences": '["Remote"]',
    }


def test_save_job_scores_empty_is_a_noop():
    db = MagicMock()
    save_job_scores(db, [])
    db.execute.assert_not_called()
    db.commit.assert_not_called()


def test_save_job_scores_commits_once():
    db = MagicMock()
    save_job_scores(db, [_score_row(1), _score_row(2)])
    db.execute.assert_called_once()
    db.commit.assert_called_once()
