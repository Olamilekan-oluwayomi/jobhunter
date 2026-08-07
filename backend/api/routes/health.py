"""Health and readiness endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from config import get_settings

router = APIRouter(tags=["meta"])


def _check_db(db: Session) -> tuple[bool, str]:
    try:
        db.execute(text("SELECT 1"))
        return True, "ok"
    except Exception:
        return False, "unreachable"


@router.get(
    "/health",
    summary="Health check",
    description=(
        "Liveness + readiness. Returns 200 when the API is up and the database "
        "responds; 503 with `db: unreachable` otherwise."
    ),
)
def health(response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    db_ok, db_status = _check_db(db)
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "time": datetime.now(timezone.utc).isoformat(),
        "checks": {"db": db_status},
    }


@router.get(
    "/ready",
    summary="Readiness probe",
    description="True readiness: database reachable. For orchestrators.",
)
def ready(response: Response, db: Session = Depends(get_db)):
    db_ok, _ = _check_db(db)
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"ready": False}
    return {"ready": True}
