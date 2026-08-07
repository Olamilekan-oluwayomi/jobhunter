"""Tests for the HTTP layer: middleware, headers, health, error handlers."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware import RateLimitMiddleware
from config import reload_settings


@pytest.fixture
def rate_limited_client(monkeypatch):
    """App with a tiny per-window limit to exercise the 429 path."""
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "3")
    reload_settings()

    mini = FastAPI()

    @mini.get("/ping")
    def ping():
        return {"ok": True}

    mini.add_middleware(RateLimitMiddleware)
    with TestClient(mini) as test_client:
        yield test_client


def test_health_returns_200_and_checks(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"db": "ok"}
    assert body["app"] == "JobHunter"
    assert "version" in body


def test_ready_returns_200(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"ready": True}


def test_request_id_header_set(client):
    response = client.get("/health")
    assert response.headers.get("x-request-id")


def test_security_headers_present(client):
    response = client.get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "no-referrer"


def test_rate_limit_returns_429_with_retry_after(rate_limited_client):
    # Limit is 3 requests per 60s window in the dedicated mini app.
    for _ in range(3):
        assert rate_limited_client.get("/ping").status_code == 200
    response = rate_limited_client.get("/ping")
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert "Too many requests" in response.json()["detail"]


def test_unknown_route_is_404_json(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_validation_error_is_422_json(client):
    response = client.get("/jobs", params={"page": -5})
    assert response.status_code == 422
    assert "detail" in response.json()
