"""Upwork scraper.

Upwork has no public job feed; its GraphQL API requires OAuth. This
scraper reads a token from the UPWORK_TOKEN environment variable and
queries the Jobs Search API when configured, returning gracefully
(and logging) when credentials are missing or the request fails.
"""

import os

from scrapers.base import BaseScraper

API_URL = "https://www.upwork.com/api/jobs/v3/search"
TOKEN_ENV = "UPWORK_TOKEN"


class UpworkScraper(BaseScraper):
    source = "Upwork"

    def fetch_jobs(self) -> list[dict]:
        token = os.getenv(TOKEN_ENV)
        if not token:
            self.logger.warning("%s not set; Upwork scraping skipped", TOKEN_ENV)
            return []

        headers = {"Authorization": f"Bearer {token}"}
        try:
            data = self.get_json_api(API_URL, headers=headers)
        except Exception as exc:
            self.logger.warning("Upwork API request failed: %s", exc)
            return []

        results = data.get("results") or data.get("jobs") or []
        jobs = [job for item in results if (job := self._build_upwork(item)) is not None]
        return jobs

    def get_json_api(self, url: str, *, headers: dict) -> object:
        response = self._session.get(url, headers=headers, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError(f"GET {url} returned HTTP {response.status_code}")
        return response.json()

    def _build_upwork(self, item: dict) -> dict | None:
        title = item.get("title") or item.get("job_title") or item.get("openingTitle")
        company = item.get("client") or item.get("company") or "Upwork"
        url = item.get("url") or item.get("ciphertext")
        if isinstance(url, dict):
            url = url.get("url")
        if url and not url.startswith("http"):
            url = f"https://www.upwork.com/jobs/{url}"
        description = (
            item.get("description") or item.get("job_description") or item.get("openingDescription")
        )
        posted_at = item.get("publishedAt") or item.get("postedDateTime") or item.get("dateCreated")
        return self.build_job(
            title=title,
            company=company,
            location=item.get("location") or "Remote",
            description=self.clean_html(description),
            url=url,
            posted_at=posted_at,
        )
