"""Shared fixtures for the JobHunter test-suite.

The suite is hermetic: it never connects to a real database or network.
Backend endpoints are exercised through FastAPI's TestClient with the DB
dependency overridden by a stub implementation.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/jobhunter_test"
os.environ["ENVIRONMENT"] = "test"
os.environ["SCHEDULE_ENABLED"] = "false"
os.environ["NOTIFICATIONS_ENABLED"] = "false"
# Generous shared limit so tests never trip the limiter; the dedicated rate
# limit test builds its own app with a tiny limit.
os.environ["RATE_LIMIT_REQUESTS"] = "100000"

import pytest
from fastapi.testclient import TestClient

from api.main import app
from config import reload_settings


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Re-read settings from the test environment before every test and
    restore the original environment afterwards."""
    reload_settings()
    yield
    reload_settings()


class StubSession:
    """Minimal stand-in for a SQLAlchemy Session used by tests that only
    assert wiring (health checks, error responses)."""

    def execute(self, statement):
        return self

    def scalars(self, statement):
        return []

    def commit(self) -> None:
        pass

    def close(self) -> None:
        pass


@pytest.fixture()
def stub_db() -> StubSession:
    return StubSession()


@pytest.fixture()
def client(stub_db: StubSession) -> TestClient:
    """A TestClient whose DB dependency is replaced with a stub, with a
    generous rate-limit so tests never trip the limiter."""
    from api.dependencies import get_db as real_get_db

    def override_get_db():
        yield stub_db

    app.dependency_overrides[real_get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides = {}
