"""Arbeitnow scraper."""

from scrapers.base import BaseScraper

API_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowScraper(BaseScraper):
    source = "Arbeitnow"

    def fetch_jobs(self) -> list[dict]:
        data = self.get_json(API_URL)
        jobs = []

        for item in data.get("data") or []:
            job = self.build_job(
                title=item.get("title"),
                company=item.get("company_name"),
                location=item.get("location"),
                description=self.clean_html(item.get("description")),
                url=item.get("url"),
                posted_at=item.get("created_at"),
            )
            if job:
                jobs.append(job)

        return jobs
