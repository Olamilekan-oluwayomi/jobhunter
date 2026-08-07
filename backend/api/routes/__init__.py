from .applications import router as applications_router
from .health import router as health_router
from .jobs import router as jobs_router
from .saved import router as saved_router
from .scrape import router as scrape_router
from .sources import router as sources_router
from .stats import router as stats_router

__all__ = [
    "applications_router",
    "health_router",
    "jobs_router",
    "saved_router",
    "scrape_router",
    "sources_router",
    "stats_router",
]
