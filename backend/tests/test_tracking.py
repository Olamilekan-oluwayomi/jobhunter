"""Tests for the application-tracking workflow.

The suite is hermetic: repository functions run against a fake session and
the CLI commands execute through typer's CliRunner with the real database
session swapped for a stub.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from cli.main import app
from database.models import Application, Job, SavedJob
from database.repository import (
    WORKFLOW_STATUSES,
    _job_status_condition,
    create_saved_job,
    upsert_application,
)

runner = CliRunner()


class FakeEntry:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


class FakeSession:
    """Stand-in for a SQLAlchemy Session covering the tracking queries."""

    def __init__(self, *, scalar=None, scalars_result=None) -> None:
        self._scalar = scalar or (lambda stmt: None)
        self._scalars_result = list(scalars_result or [])
        self.added: list = []
        self.commits = 0
        self.refreshed: list = []

    def get(self, model, ident):
        return None

    def scalar(self, stmt):
        return self._scalar(stmt)

    def scalars(self, stmt):
        out = self._scalars_result

        class _Rows:
            def unique(self):
                return self

            def all(self):
                return out

        return _Rows()

    def add(self, obj) -> None:
        self.added.append(obj)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, obj) -> None:
        self.refreshed.append(obj)

    def close(self) -> None:
        pass


def _job(id_: int, *, title: str = "Frontend Engineer", score: int | None = None) -> FakeEntry:
    return FakeEntry(
        id=id_,
        title=title,
        company="Acme",
        location="Remote",
        url=f"https://example.com/{id_}",
        source="Remotive",
        match_score=FakeEntry(score=score) if score is not None else None,
    )


# --- repository: save ----------------------------------------------------


def test_create_saved_job_creates_entry():
    db = FakeSession()
    entry = create_saved_job(db, 1)
    assert entry is not None
    assert db.added == [entry]
    assert db.commits == 1


def test_create_saved_job_is_idempotent_no_duplicate():
    db = FakeSession(scalar=lambda stmt: object())  # an entry already exists
    assert create_saved_job(db, 1) is None
    assert db.added == []
    assert db.commits == 0


# --- repository: upsert application --------------------------------------


def test_upsert_application_creates_when_none_exists():
    db = FakeSession(scalar=lambda stmt: None)
    entry = upsert_application(db, 7, "applied", notes="through careers page")
    assert entry.job_id == 7
    assert entry.status == "applied"
    assert entry.notes == "through careers page"
    assert db.added == [entry]
    assert db.commits == 1


def test_upsert_application_updates_existing_record():
    existing = FakeEntry(job_id=7, status="rejected", notes="old", applied_at=None)
    db = FakeSession(scalar=lambda stmt: existing)
    entry = upsert_application(db, 7, "applied", notes="reapplied")
    assert entry is existing
    assert existing.status == "applied"
    assert existing.notes == "reapplied"
    assert db.added == []
    assert db.commits == 1


def test_upsert_application_preserves_notes_and_applied_at_when_omitted():
    existing = FakeEntry(job_id=7, status="interview", notes="keep me", applied_at="2026-08-01")
    db = FakeSession(scalar=lambda stmt: existing)
    upsert_application(db, 7, "applied")
    assert existing.status == "applied"
    assert existing.notes == "keep me"
    assert existing.applied_at == "2026-08-01"


# --- repository: status filtering ----------------------------------------


@pytest.mark.parametrize("status", WORKFLOW_STATUSES)
def test_workflow_statuses_compile_to_sql(status):
    stmt = select(Job).where(_job_status_condition(status))
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "WHERE" in sql
    assert "exists" in sql.lower()


def test_saved_status_requires_no_application():
    sql = str(
        select(Job)
        .where(_job_status_condition("saved"))
        .compile(compile_kwargs={"literal_binds": True})
    )
    assert "saved_jobs" in sql
    assert "applications" in sql


def test_application_status_filters_by_status_value():
    sql = str(
        select(Job)
        .where(_job_status_condition("interview"))
        .compile(compile_kwargs={"literal_binds": True})
    )
    assert "applications" in sql
    assert "interview" in sql


# --- CLI: save / apply / saved ------------------------------------------


def _invoke(args, **fake_kwargs):
    import cli.main as cli

    fake = FakeSession(**fake_kwargs)
    original = cli.SessionLocal
    cli.SessionLocal = lambda: fake
    try:
        result = runner.invoke(app, args)
        return result, fake
    finally:
        cli.SessionLocal = original


def _invoke_with_job(args, job, **fake_kwargs):
    with patch("cli.main.repo.get_job", return_value=job):
        return _invoke(args, **fake_kwargs)


def test_save_command_records_and_confirms():
    result, _ = _invoke_with_job(["save", "1"], _job(1, score=92))
    assert result.exit_code == 0
    assert "Saved job #1" in result.output
    assert "Frontend Engineer" in result.output
    assert "Acme" in result.output
    assert "Match: 92" in result.output


def test_save_nonexistent_job_fails():
    result, _ = _invoke_with_job(["save", "999"], None)
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_save_same_job_twice_is_idempotent():
    first, _ = _invoke_with_job(["save", "1"], _job(1), scalar=lambda stmt: None)
    second, _ = _invoke_with_job(["save", "1"], _job(1), scalar=lambda stmt: object())
    assert "Saved job #1" in first.output
    assert "already saved" in second.output


def test_apply_command_records_application():
    result, fake = _invoke_with_job(
        ["apply", "5", "--notes", "careers page"], _job(5), scalar=lambda stmt: None
    )
    assert result.exit_code == 0
    assert "Application recorded" in result.output
    assert "Frontend Engineer" in result.output
    assert "Acme" in result.output
    assert "Status: applied" in result.output
    assert fake.added


def test_apply_nonexistent_job_fails():
    result, _ = _invoke_with_job(["apply", "999"], None)
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_apply_updates_existing_no_duplicate():
    existing = FakeEntry(job_id=5, status="interview", notes=None, applied_at=None)
    result, fake = _invoke_with_job(
        ["apply", "5", "--notes", "reapplied"], _job(5), scalar=lambda stmt: existing
    )
    assert result.exit_code == 0
    assert existing.status == "applied"
    assert existing.notes == "reapplied"
    assert fake.added == []


# --- CLI: status ----------------------------------------------------------


@pytest.mark.parametrize("status", ("applied", "interview", "rejected", "offer"))
def test_status_command_accepts_each_application_status(status):
    result, fake = _invoke_with_job(["status", "5", status], _job(5))
    assert result.exit_code == 0
    assert "Job #5 status updated" in result.output
    assert "Frontend Engineer" in result.output
    assert "Acme" in result.output
    assert f"Status: {status}" in result.output
    assert fake.added and isinstance(fake.added[0], Application)


def test_status_saved_uses_saved_jobs_workflow():
    result, fake = _invoke_with_job(["status", "5", "saved"], _job(5))
    assert result.exit_code == 0
    assert "Job #5 status updated" in result.output
    assert "Status: saved" in result.output
    assert fake.added and isinstance(fake.added[0], SavedJob)


def test_status_saved_idempotent_when_already_saved():
    result, fake = _invoke_with_job(["status", "5", "saved"], _job(5), scalar=lambda stmt: object())
    assert result.exit_code == 0
    assert "Status: saved" in result.output
    assert fake.added == []


def test_status_invalid_status_fails():
    result, _ = _invoke(["status", "5", "bogus"])
    assert result.exit_code == 1
    assert "Invalid status" in result.output
    assert "saved, applied, interview, rejected, offer" in result.output


def test_status_nonexistent_job_fails():
    result, _ = _invoke_with_job(["status", "999", "interview"], None)
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_status_updates_existing_record_preserving_notes_and_applied_at():
    existing = FakeEntry(job_id=5, status="applied", notes="keep me", applied_at="2026-08-01")
    result, fake = _invoke_with_job(
        ["status", "5", "interview"], _job(5), scalar=lambda stmt: existing
    )
    assert result.exit_code == 0
    assert existing.status == "interview"
    assert existing.notes == "keep me"
    assert existing.applied_at == "2026-08-01"
    assert fake.added == []


def test_saved_command_lists_with_score_and_status():
    saved_entry = FakeEntry(
        job=FakeEntry(
            id=3,
            title="React Developer",
            company="Beta",
            location="Remote",
            match_score=FakeEntry(score=88),
            applications=[FakeEntry(status="applied")],
        )
    )
    result, _ = _invoke(["saved"], scalars_result=[saved_entry])
    assert result.exit_code == 0
    assert "React Developer" in result.output
    assert "88" in result.output
    assert "applied" in result.output


def test_saved_command_empty():
    result, _ = _invoke(["saved"], scalars_result=[])
    assert result.exit_code == 0
    assert "No saved jobs yet" in result.output
