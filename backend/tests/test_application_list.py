from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Application, Base, Job, Source
from database.repository import list_applications


def test_application_list_pagination_status_and_stable_order():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Source(name="Test"))
        for index in range(1, 4):
            db.add(
                Job(
                    id=index,
                    title=f"Engineer {index}",
                    company="Acme",
                    url=f"https://example.com/{index}",
                    source="Test",
                )
            )
        db.flush()
        for index, state in enumerate(["applied", "interview", "applied"], start=1):
            db.add(
                Application(id=index, job_id=index, status=state, applied_at=datetime(2026, 10, 20))
            )
        db.commit()
        rows, total = list_applications(db, page=1, page_size=1, status="applied")
        assert total == 2
        assert [row.id for row in rows] == [3]
        assert rows[0].job.title == "Engineer 3"
        rows, total = list_applications(db, page=2, page_size=1, status="applied")
        assert [row.id for row in rows] == [1]
        assert total == 2
        rows, total = list_applications(db, status="offer")
        assert rows == []
        assert total == 0
    engine.dispose()


def test_application_list_http_contract(client):
    with patch("api.routes.applications.repo.list_applications", return_value=([], 0)) as listing:
        response = client.get("/applications?page=2&page_size=10&status=interview")
        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0, "page": 2, "page_size": 10}
        assert listing.call_args.kwargs == {"page": 2, "page_size": 10, "status": "interview"}


@pytest.mark.parametrize("query", ["page=0", "page_size=101", "page_size=0", "status=unknown"])
def test_application_list_rejects_invalid_filters(client, query):
    response = client.get(f"/applications?{query}")
    assert response.status_code == 422
