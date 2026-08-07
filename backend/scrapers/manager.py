"""Concurrent scraper orchestration.

Runs every configured scraper in a thread pool, isolates failures so one
unavailable source never blocks the others, dedupes jobs by URL and records
a per-source ``ScraperResult`` (raw/parsed counts + health status) for the
CLI, scheduler and API to report.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from urllib.parse import urlsplit

from config import get_settings
from scrapers.arbeitnow import ArbeitnowScraper
from scrapers.base import BaseScraper, ScraperError
from scrapers.jobicy import JobicyScraper
from scrapers.reddit import RedditScraper
from scrapers.remoteok import RemoteOKScraper
from scrapers.remotive import RemotiveScraper
from scrapers.upwork import UpworkScraper
from utils.logger import get_logger

ALL_SCRAPERS = (
    RemotiveScraper,
    RemoteOKScraper,
    JobicyScraper,
    ArbeitnowScraper,
    RedditScraper,
    UpworkScraper,
)


@dataclass
class ScraperResult:
    """Outcome of one scraper run.

    - ``raw``    items fetched from the source before normalization
    - ``parsed`` jobs after normalization (what ``fetch_jobs`` returned)
    - ``new``    genuinely new rows persisted by the caller
    - ``status`` health label: OK | HTTP <code> | UNAVAILABLE | DISABLED
                 | TIMEOUT | EMPTY | FAILED
    """

    source: str
    raw: int = 0
    parsed: int = 0
    new: int = 0
    status: str = "OK"
    message: str = ""
    elapsed: float = 0.0


def _url_key(url: str) -> str:
    """Canonical URL key for duplicate detection."""
    parts = urlsplit(url)
    host = (parts.netloc or "").lower()
    path = (parts.path or "").rstrip("/")
    return f"{host}{path}"


def _scraper_config(source: str, settings) -> tuple[bool, float, int]:
    """Resolve (enabled, timeout, retries) for a source from settings."""
    if source == "Reddit":
        return settings.reddit_enabled, settings.reddit_timeout, settings.reddit_max_retries
    if source == "Upwork":
        return settings.upwork_enabled, settings.upwork_timeout, settings.upwork_max_retries
    return True, settings.scraper_timeout, settings.scraper_max_retries


def build_scrapers(source_filter: str | None = None) -> tuple[list[BaseScraper], list[str]]:
    """Instantiate scrapers honoring per-source config.

    Returns ``(active_scrapers, disabled_sources)``. ``source_filter`` is a
    comma-separated list of source names (None = all).
    """
    settings = get_settings()
    selected = {s.strip() for s in source_filter.split(",")} if source_filter else None

    scrapers: list[BaseScraper] = []
    disabled: list[str] = []
    for cls in ALL_SCRAPERS:
        if selected and cls.source not in selected:
            continue
        enabled, timeout, retries = _scraper_config(cls.source, settings)
        if not enabled:
            disabled.append(cls.source)
            continue
        scrapers.append(cls(timeout=timeout, max_retries=retries))
    return scrapers, disabled


class ScraperManager:
    def __init__(
        self,
        scrapers: list[BaseScraper] | None = None,
        disabled_sources: list[str] | None = None,
    ) -> None:
        if scrapers is None:
            scrapers, disabled_sources = build_scrapers()
        self.scrapers = scrapers
        self.disabled_sources = disabled_sources or []
        self.results: dict[str, ScraperResult] = {}
        self.logger = get_logger("scrapers.manager")

    def fetch_all(
        self,
        *,
        max_workers: int | None = None,
        on_source_done: "callable | None" = None,
    ) -> list[dict]:
        """Run all scrapers concurrently, dedupe jobs by URL and record a
        per-source ``ScraperResult``. One failing source never blocks the
        others. ``on_source_done(result)`` is invoked as each source finishes.

        Returns every normalized job dict for later persistence.
        """
        self.results = {
            source: ScraperResult(
                source=source, status="DISABLED", message="disabled in configuration"
            )
            for source in self.disabled_sources
        }
        seen: set[str] = set()
        jobs: list[dict] = []
        started = time.perf_counter()

        with ThreadPoolExecutor(max_workers=max_workers or max(1, len(self.scrapers))) as pool:
            futures = {pool.submit(self._run, scraper): scraper for scraper in self.scrapers}
            for future in as_completed(futures):
                scraper = futures[future]
                source_jobs = future.result()
                if on_source_done is not None:
                    on_source_done(self.results.get(scraper.source))
                for job in source_jobs:
                    key = _url_key(job["url"])
                    if key in seen:
                        self.logger.debug("duplicate skipped: %s", job["url"])
                        continue
                    seen.add(key)
                    jobs.append(job)

        elapsed = time.perf_counter() - started
        self.logger.info(
            "fetch_all complete: %s sources, %s new jobs, %.2fs elapsed",
            len(self.scrapers),
            len(jobs),
            elapsed,
        )
        return jobs

    def _run(self, scraper: BaseScraper) -> list[dict]:
        started = time.perf_counter()
        scraper._begin_fetch()
        try:
            jobs = scraper.fetch_jobs()
            status = scraper.status or "OK"
            message = scraper.status_message or ""
        except Exception as exc:
            jobs = []
            if isinstance(exc, ScraperError):
                if exc.status_code:
                    status = f"HTTP {exc.status_code}"
                elif exc.timed_out:
                    status = "TIMEOUT"
                else:
                    status = "FAILED"
            else:
                status = (
                    getattr(scraper, "status", "FAILED")
                    if getattr(scraper, "status", "OK") != "OK"
                    else "FAILED"
                )
            message = getattr(scraper, "status_message", "") or str(exc)
            self.logger.error(
                "%s failed after %.2fs: %s",
                scraper.source,
                time.perf_counter() - started,
                exc,
            )

        result = ScraperResult(
            source=scraper.source,
            raw=getattr(scraper, "raw_count", 0),
            parsed=len(jobs),
            status=status,
            message=message,
            elapsed=time.perf_counter() - started,
        )
        self.results[scraper.source] = result
        self.logger.info(
            "%s: status=%s raw=%s parsed=%s in %.2fs%s",
            scraper.source,
            result.status,
            result.raw,
            result.parsed,
            result.elapsed,
            f" ({result.message})" if result.message else "",
        )
        return jobs
