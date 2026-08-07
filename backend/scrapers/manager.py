"""Concurrent scraper orchestration."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit

from scrapers.arbeitnow import ArbeitnowScraper
from scrapers.base import BaseScraper
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


def _url_key(url: str) -> str:
    """Canonical URL key for duplicate detection."""
    parts = urlsplit(url)
    host = (parts.netloc or "").lower()
    path = (parts.path or "").rstrip("/")
    return f"{host}{path}"


class ScraperManager:
    def __init__(self, scrapers: list[BaseScraper] | None = None) -> None:
        self.scrapers = scrapers or [cls() for cls in ALL_SCRAPERS]
        self.logger = get_logger("scrapers.manager")

    def fetch_all(self, *, max_workers: int | None = None) -> list[dict]:
        """Run all scrapers concurrently, dedupe jobs by URL and log
        per-source results, failures and durations."""
        seen: set[str] = set()
        jobs: list[dict] = []
        started = time.perf_counter()

        with ThreadPoolExecutor(max_workers=max_workers or len(self.scrapers)) as pool:
            futures = {pool.submit(self._run, scraper): scraper for scraper in self.scrapers}
            for future in as_completed(futures):
                source_jobs = future.result()
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
        try:
            jobs = scraper.fetch_jobs()
            self.logger.info(
                "%s returned %s jobs in %.2fs",
                scraper.source,
                len(jobs),
                time.perf_counter() - started,
            )
            return jobs
        except Exception as exc:
            self.logger.error(
                "%s failed after %.2fs: %s",
                scraper.source,
                time.perf_counter() - started,
                exc,
            )
            return []
