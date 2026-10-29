"""Real SQL-backed journeys: authentication, isolation, score caching and pagination."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.auth import COOKIE, _attempts
from api.dependencies import get_db
from api.main import app
from database.models import (
    Application,
    Base,
    CandidateScore,
    Job,
    LoginSession,
    SavedJob,
    Source,
    User,
)
from utils.time import utcnow

PASSWORD = "a long test password 42"
HEADERS = {"X-Requested-With": "JobHunter"}


@pytest.fixture
def account_db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=1, email="legacy@jobhunter.invalid", is_active=False))
        db.add(Source(name="Test"))
        db.flush()
        db.add_all(
            [
                Job(
                    id=i,
                    title="Frontend Engineer" if i % 2 else "C Developer",
                    company=f"Company {i}",
                    source="Test",
                    url=f"https://example.com/{i}",
                    description="React and TypeScript. Full-time remote role.",
                    location="Worldwide",
                    posted_at=datetime(2026, 10, 20),
                )
                for i in range(1, 26)
            ]
        )
        db.commit()

    def dependency():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = dependency
    _attempts.clear()
    try:
        yield engine
    finally:
        app.dependency_overrides.clear()
        _attempts.clear()
        engine.dispose()


def register(client, email):
    response = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    return response.json()


def test_authentication_cookie_logout_and_expiry(account_db):
    with TestClient(app, headers=HEADERS) as client:
        assert client.get("/applications").status_code == 401
        response = client.post(
            "/auth/register", json={"email": "Alice@Example.com", "password": PASSWORD}
        )
        assert response.status_code == 201
        assert "httponly" in response.headers["set-cookie"].lower()
        assert "samesite=lax" in response.headers["set-cookie"].lower()
        assert response.json()["email"] == "alice@example.com"
        token = client.cookies[COOKIE]
        with Session(account_db) as db:
            assert db.get(LoginSession, token) is None
            user = db.scalar(select(User).where(User.email == "alice@example.com"))
            assert PASSWORD not in user.password_hash
        assert client.get("/auth/me").status_code == 200
        assert client.post("/auth/logout").status_code == 204
        client.cookies.set(COOKIE, token)
        assert client.get("/auth/me").status_code == 401
        assert (
            client.post(
                "/auth/login", json={"email": "alice@example.com", "password": PASSWORD}
            ).status_code
            == 200
        )
        with Session(account_db) as db:
            row = db.scalar(select(LoginSession))
            row.expires_at = utcnow() - timedelta(seconds=1)
            db.commit()
        assert client.get("/auth/me").status_code == 401


def test_two_users_cannot_read_or_modify_each_others_records(account_db):
    with TestClient(app, headers=HEADERS) as alice, TestClient(app, headers=HEADERS) as bob:
        a = register(alice, "alice@example.com")
        register(bob, "bob@example.com")
        saved = alice.post("/save-job", json={"job_id": 1}).json()
        application = alice.post(
            "/applications", json={"job_id": 1, "notes": "Private note"}
        ).json()
        assert bob.get("/saved").json() == []
        assert bob.get("/applications").json()["total"] == 0
        assert bob.get("/stats").json()["total_saved"] == 0
        assert bob.get("/workspace-index").json() == {"saved": [], "applications": []}
        assert bob.delete(f"/save-job/{saved['id']}").status_code == 404
        assert (
            bob.patch(f"/applications/{application['id']}", json={"notes": "stolen"}).status_code
            == 404
        )
        assert bob.post("/save-job", json={"job_id": 1}).status_code == 201
        assert bob.post("/applications", json={"job_id": 1}).status_code == 201
        assert alice.get("/applications").json()["items"][0]["notes"] == "Private note"
        with Session(account_db) as db:
            assert (
                db.scalar(
                    select(func.count()).select_from(SavedJob).where(SavedJob.user_id == a["id"])
                )
                == 1
            )


def test_profile_scoring_cache_pagination_filters_and_detail(account_db):
    with TestClient(app, headers=HEADERS) as client:
        user = register(client, "alice@example.com")
        profile = {
            "name": "Alice",
            "role": "Frontend Engineer",
            "location": "Nigeria",
            "skills": ["React", "TypeScript"],
            "remote": True,
        }
        assert client.put("/auth/profile", json=profile).status_code == 200
        first = client.get("/discovery?page_size=5").json()
        second = client.get("/discovery?page_size=5&page=2").json()
        assert first["total"] == 25
        assert len(first["items"]) == 5
        assert not ({row["id"] for row in first["items"]} & {row["id"] for row in second["items"]})
        item = first["items"][0]
        assert item["match"]["score"] == 70
        assert item["match"]["matched_skills"] == ["React", "TypeScript"]
        assert item["description"] is None
        detail = client.get(f"/discovery/{item['id']}").json()
        assert detail["match"] == item["match"]
        assert detail["description"]
        assert client.get("/discovery?search=Company%2025").json()["total"] == 1
        assert client.get("/discovery?employment_type=Contract").json()["total"] == 0
        client.post("/save-job", json={"job_id": 25})
        assert client.get("/discovery?saved_only=true").json()["total"] == 1
        with Session(account_db) as db:
            assert db.scalar(select(func.count()).select_from(CandidateScore)) == 25
            assert db.scalar(select(CandidateScore.user_id).limit(1)) == user["id"]
        profile["skills"] = ["C++"]
        client.put("/auth/profile", json=profile)
        updated = client.get("/discovery").json()
        assert updated["items"][0]["match"]["matched_skills"] == []


def test_csrf_admin_and_sensitive_validation(account_db):
    with TestClient(app, headers=HEADERS) as client:
        register(client, "alice@example.com")
        assert client.post("/scrape").status_code == 403
        assert client.get("/scrape-runs").status_code == 403
        assert (
            client.put(
                "/auth/profile", json={}, headers={"Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        client.headers.pop("X-Requested-With")
        assert client.post("/save-job", json={"job_id": 1}).status_code == 403
        response = client.post(
            "/auth/login",
            headers=HEADERS,
            json={"email": "alice@example.com", "password": "secret"},
        )
        assert response.status_code == 422
        assert "secret" not in response.text


def test_registration_does_not_claim_legacy_data(account_db):
    with Session(account_db) as db:
        db.add(Application(job_id=1, user_id=1, notes="Old private note"))
        db.commit()
    with TestClient(app, headers=HEADERS) as client:
        register(client, "alice@example.com")
        assert client.get("/applications").json()["total"] == 0


def test_application_patches_change_only_supplied_fields(account_db):
    with TestClient(app, headers=HEADERS) as client:
        register(client, "alice@example.com")
        created = client.post("/applications", json={"job_id": 1, "notes": "Keep me"}).json()
        path = f"/applications/{created['id']}"
        assert client.patch(path, json={"status": "interview"}).json()["notes"] == "Keep me"
        updated = client.patch(path, json={"notes": "New note"}).json()
        assert updated["status"] == "interview"
        assert updated["notes"] == "New note"
        assert client.patch(path, json={"notes": None}).json()["notes"] is None


@pytest.mark.parametrize("location", ["Not worldwide", "Worldwide except US residents"])
def test_negative_location_evidence_is_not_marked_eligible(location):
    from matching.discovery import job_metadata

    job = Job(title="Engineer", location=location)
    assert job_metadata(job, {"location": "United States"})["eligibility"]["status"] == "unknown"
