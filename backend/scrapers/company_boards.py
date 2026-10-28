"""Read configured company boards through documented public GET endpoints.

Board entries are `slug` or `slug|Company Name`. No credentials or application
submission endpoints are used. Empty configuration makes these sources disabled.
"""

import re
from html import unescape

from config import get_settings
from scrapers.base import BaseScraper, ScraperError

MAX_BOARDS = 25
LEVER_PAGE_SIZE = 100
LEVER_MAX_PAGES = 10


class CompanyBoardScraper(BaseScraper):
    def board_entries(self) -> list[str]:
        raise NotImplementedError

    def fetch_board(self, slug: str, company: str) -> list[dict]:
        raise NotImplementedError

    def fetch_jobs(self) -> list[dict]:
        self._begin_fetch()
        entries = list(dict.fromkeys(self.board_entries()))
        if not entries:
            self.status = "DISABLED"
            self.status_message = "No company boards configured"
            return []
        if len(entries) > MAX_BOARDS:
            raise ScraperError(f"Configure at most {MAX_BOARDS} {self.source} boards per run")
        jobs = []
        failures = []
        succeeded = 0
        for entry in entries:
            slug, separator, label = entry.partition("|")
            slug = slug.strip()
            company = label.strip() if separator else slug
            if not re.fullmatch(r"[A-Za-z0-9_-]+", slug) or not company:
                failures.append(f"Invalid board entry: {entry}")
                continue
            try:
                jobs.extend(self.fetch_board(slug, company))
                succeeded += 1
            except (ScraperError, TypeError, ValueError, AttributeError) as exc:
                failures.append(f"{slug}: {exc}")
        if failures:
            self.status = "PARTIAL" if succeeded else "FAILED"
            self.status_message = "; ".join(failures)
        return jobs

    def text(self, value: str | None) -> str:
        return self.clean_html(unescape(value or ""))


class LeverScraper(CompanyBoardScraper):
    source = "Lever"

    def board_entries(self) -> list[str]:
        return get_settings().lever_boards

    def fetch_board(self, slug: str, company: str) -> list[dict]:
        jobs = []
        for page in range(LEVER_MAX_PAGES):
            payload = self.get_json(
                f"https://api.lever.co/v0/postings/{slug}",
                params={"mode": "json", "skip": page * LEVER_PAGE_SIZE, "limit": LEVER_PAGE_SIZE},
            )
            if not isinstance(payload, list):
                raise ScraperError("Expected a postings list")
            for item in payload:
                if not isinstance(item, dict):
                    raise ScraperError("Invalid posting object")
                categories = item.get("categories") or {}
                location = categories.get("location") or ""
                workplace = item.get("workplaceType") or ""
                location = " · ".join(value for value in (workplace, location) if value)
                salary = item.get("salaryRange") or {}
                amounts = [salary.get("min"), salary.get("max")]
                pay = "-".join(str(value) for value in amounts if value is not None)
                if pay:
                    currency = salary.get("currency", "")
                    interval = salary.get("interval", "unspecified")
                    pay = f"{currency} {pay} / {interval}"
                description = [item.get("descriptionPlain") or item.get("description") or ""]
                for section in item.get("lists") or []:
                    description.extend([section.get("text") or "", section.get("content") or ""])
                description.append(item.get("additionalPlain") or item.get("additional") or "")
                description.append(categories.get("commitment") or "")
                job = self.build_job(
                    title=item.get("text"),
                    company=company,
                    location=location,
                    salary=pay or None,
                    description=self.text("\n".join(description)),
                    url=item.get("hostedUrl"),
                    # The public API does not guarantee a posting date.
                    posted_at=None,
                )
                if job:
                    jobs.append(job)
            if len(payload) < LEVER_PAGE_SIZE:
                return jobs
        # Never present a capped board as a complete successful fetch.
        raise ScraperError(f"Board exceeds the {LEVER_MAX_PAGES}-page fetch limit")


class AshbyScraper(CompanyBoardScraper):
    source = "Ashby"

    def board_entries(self) -> list[str]:
        return get_settings().ashby_boards

    def fetch_board(self, slug: str, company: str) -> list[dict]:
        payload = self.get_json(
            f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
            params={"includeCompensation": "true"},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ScraperError("Expected a jobs list")
        jobs = []
        for item in payload["jobs"]:
            if not isinstance(item, dict):
                raise ScraperError("Invalid posting object")
            # Unlisted positions must not be exposed in an aggregated board.
            if item.get("isListed") is not True:
                continue
            locations = [item.get("location") or ""]
            locations.extend(
                place.get("location") or "" for place in item.get("secondaryLocations") or []
            )
            # isRemote can also mean hybrid; prefer the explicit workplace type.
            workplace = item.get("workplaceType") or ""
            location = " · ".join(
                dict.fromkeys(value for value in [workplace, *locations] if value)
            )
            compensation = item.get("compensation") or {}
            job = self.build_job(
                title=item.get("title"),
                company=company,
                location=location,
                salary=compensation.get("scrapeableCompensationSalarySummary"),
                description=self.text(
                    (item.get("descriptionPlain") or item.get("descriptionHtml") or "")
                    + "\n"
                    + (item.get("employmentType") or "")
                ),
                url=item.get("jobUrl"),
                posted_at=item.get("publishedAt"),
            )
            if job:
                jobs.append(job)
        return jobs
