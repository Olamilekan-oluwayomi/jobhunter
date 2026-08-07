from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import register_exception_handlers
from api.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from api.routes import (
    applications_router,
    health_router,
    jobs_router,
    saved_router,
    scrape_router,
    sources_router,
    stats_router,
)
from config import get_settings
from scheduler.runner import Scheduler
from utils.logger import configure_logging, get_logger

configure_logging()
settings = get_settings()
logger = get_logger("api.main")

DESCRIPTION = """
JobHunter API — job aggregation with search, filtering and sorting.

## Jobs
- `GET /jobs` — paginated list with search, filters and sorting
- `GET /jobs/{id}` — single job detail

## Sources
- `GET /sources` — all job sources with job counts

## Saved jobs
- `GET /saved` — list saved jobs
- `POST /save-job` — save a job
- `DELETE /save-job/{id}` — unsave a job

## Applications
- `POST /applications` — create an application
- `PATCH /applications/{id}` — update status/notes

## Miscellaneous
- `GET /stats` — aggregate counters
- `GET /health` — health/readiness
- `POST /scrape` — trigger a full scrape (inserts new jobs, sends matched notifications)
- `GET /scrape-runs` — recent automated scrape executions
"""

_scheduler: Scheduler | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _scheduler
    if settings.schedule_enabled:
        _scheduler = Scheduler()
        _scheduler.start()
    else:
        logger.info("Scheduler disabled via SCHEDULE_ENABLED=0.")
    yield
    if _scheduler:
        _scheduler.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=DESCRIPTION,
    contact={"name": "JobHunter"},
    license_info={"name": "MIT"},
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.debug,
)

register_exception_handlers(app)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    jobs_router,
    stats_router,
    sources_router,
    saved_router,
    applications_router,
    scrape_router,
    health_router,
):
    app.include_router(router)


@app.get("/", summary="Service info", tags=["meta"])
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs",
        "health": "/health",
    }
