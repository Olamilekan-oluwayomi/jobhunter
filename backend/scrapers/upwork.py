"""Upwork scraper.

Upwork has no public, unauthenticated job feed. Its GraphQL API
(api.upwork.com/graphql) and the legacy REST search endpoint
(www.upwork.com/api/v3/jobs/search) both require OAuth 2.0 credentials.

This scraper is deliberately honest about that: when no valid access
token is configured (``UPWORK_TOKEN``) it reports the source as
UNAVAILABLE instead of fabricating results. When a token is present it
queries the documented REST endpoint and logs credential-free
diagnostics (URL, status, content type, raw/parsed/filtered counts).
Credentials are never logged.
"""

import os

from scrapers.base import BaseScraper, ScraperError

API_URL = "https://www.upwork.com/api/v3/jobs/search"
TOKEN_ENV = "UPWORK_TOKEN"
SEARCH_PARAMS = {"q": "remote", "paging": "0;25"}


class UpworkScraper(BaseScraper):
    source = "Upwork"

    def fetch_jobs(self) -> list[dict]:
        self._begin_fetch()
        token = os.getenv(TOKEN_ENV)
        if not token:
            self.status = "UNAVAILABLE"
            self.status_message = (
                f"{TOKEN_ENV} not set - Upwork requires OAuth credentials to read job postings"
            )
            self.logger.warning("%s", self.status_message)
            return []

        self.logger.debug("GET %s (Authorization: Bearer <redacted>)", API_URL)
        try:
            response = self.get(
                API_URL,
                params=SEARCH_PARAMS,
                headers={"Authorization": f"Bearer {token}"},
            )
        except ScraperError as exc:
            self._handle_error(exc)
            return []

        content_type = response.headers.get("Content-Type", "")
        self.logger.debug("GET %s -> HTTP %s (%s)", API_URL, response.status_code, content_type)
        if response.status_code != 200:
            self._handle_error(
                ScraperError(
                    f"GET {API_URL} returned HTTP {response.status_code}",
                    status_code=response.status_code,
                )
            )
            return []

        try:
            data = response.json()
        except ValueError:
            self.status = "FAILED"
            self.status_message = "Upwork returned a non-JSON response"
            self.logger.warning("%s", self.status_message)
            return []

        results = data.get("jobs") or data.get("results") or []
        if not isinstance(results, list):
            self.status = "FAILED"
            self.status_message = "Upwork response had an unexpected structure (no job list)"
            self.logger.warning("%s", self.status_message)
            return []

        jobs = [job for item in results if (job := self._build_upwork(item)) is not None]
        self.logger.info(
            "Upwork: HTTP %s, raw=%s parsed=%s filtered=%s",
            response.status_code,
            len(results),
            len(jobs),
            len(results) - len(jobs),
        )
        return jobs

    def _handle_error(self, exc: Exception) -> None:
        code = getattr(exc, "status_code", None)
        if code in (401, 403):
            self.status = f"HTTP {code}"
            self.status_message = (
                "Upwork rejected the credentials — OAuth token missing, invalid or expired"
            )
        elif getattr(exc, "timed_out", False):
            self.status = "TIMEOUT"
            self.status_message = f"Upwork request timed out: {exc}"
        else:
            self.status = "FAILED"
            self.status_message = str(exc)
        self.logger.warning("%s", self.status_message)

    def _build_upwork(self, item: dict) -> dict | None:
        title = item.get("title") or item.get("job_title") or item.get("openingTitle")
        company = item.get("client") or item.get("company") or "Upwork"
        url = item.get("url") or item.get("ciphertext") or item.get("id")
        if isinstance(url, dict):
            url = url.get("url")
        if url and not url.startswith("http"):
            url = f"https://www.upwork.com/jobs/{url}"
        description = (
            item.get("description") or item.get("job_description") or item.get("openingDescription")
        )
        posted_at = (
            item.get("publishedAt")
            or item.get("postedDateTime")
            or item.get("dateCreated")
            or item.get("createdDateTime")
        )
        return self.build_job(
            title=title,
            company=company,
            location=item.get("location") or "Remote",
            description=self.clean_html(description),
            url=url,
            posted_at=posted_at,
        )
