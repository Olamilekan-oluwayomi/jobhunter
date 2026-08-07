"""Base scraper interface and shared HTTP/normalization helpers."""

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.logger import get_logger

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")

REQUIRED_FIELDS = ("title", "company", "url", "source")
OPTIONAL_FIELDS = ("location", "salary", "description", "posted_at")

DEFAULT_TIMEOUT = 15.0
DEFAULT_RETRIES = 3
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
RETRY_BACKOFF = 0.5


class ScraperError(RuntimeError):
    """Raised when a scraper fails to fetch or parse a source."""


class BaseScraper(ABC):
    """Base class every job scraper must inherit.

    Provides a retrying, timing-out HTTP session plus helpers for
    cleaning text, parsing dates and normalizing raw jobs into the
    single app-wide job schema:

        {
            "title": str,
            "company": str,
            "location": str | None,
            "salary": str | None,
            "description": str | None,
            "url": str,
            "source": str,
            "posted_at": datetime | None,
        }
    """

    source: str = ""

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_RETRIES,
    ) -> None:
        if not self.source:
            raise ValueError(f"{type(self).__name__} must define `source`")
        self.timeout = timeout
        self.logger: logging.Logger = get_logger(f"scraper.{self.source}")

        retry = Retry(
            total=max_retries,
            backoff_factor=RETRY_BACKOFF,
            status_forcelist=tuple(RETRY_STATUS_CODES),
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,
        )
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "JobHunter/1.0 (job aggregation)",
                "Accept": "application/json",
            }
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    @abstractmethod
    def fetch_jobs(self) -> list[dict]:
        """Fetch and normalize jobs from this source."""

    def get_json(self, url: str, *, params: dict | None = None) -> Any:
        """GET a JSON resource with retry and timeout, raising ScraperError on failure."""
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ScraperError(f"request failed: {exc}") from exc

        if response.status_code != 200:
            raise ScraperError(f"GET {url} returned HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise ScraperError(f"GET {url} returned invalid JSON") from exc

    @staticmethod
    def clean_html(value: str | None) -> str:
        """Strip HTML tags and collapse whitespace."""
        if not value:
            return ""
        text = HTML_TAG_RE.sub(" ", value)
        return WHITESPACE_RE.sub(" ", text).strip()

    @staticmethod
    def parse_posted_at(value: Any) -> datetime | None:
        """Parse a source-specific date into a timezone-aware datetime."""
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def validate_url(value: str | None) -> bool:
        """Return True only for http(s) URLs with a hostname."""
        if not value:
            return False
        try:
            parsed = urlparse(value)
        except ValueError:
            return False
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    def build_job(self, **fields: Any) -> dict | None:
        """Validate and normalize raw fields into the app job schema.

        Returns None if the entry is missing required data, has an
        invalid URL, or has a title too short to be a real job posting.
        """
        title = str(fields.get("title") or "").strip()
        company = str(fields.get("company") or "").strip()
        url = str(fields.get("url") or "").strip()

        if len(title) < 3 or not company:
            return None
        if not self.validate_url(url):
            return None

        return {
            "title": title,
            "company": company,
            "location": str(fields.get("location") or "").strip() or None,
            "salary": str(fields.get("salary") or "").strip() or None,
            "description": fields.get("description"),
            "url": url,
            "source": self.source,
            "posted_at": self.parse_posted_at(fields.get("posted_at")),
        }
