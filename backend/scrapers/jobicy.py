"""Jobicy scraper."""

from scrapers.base import BaseScraper

API_URL = "https://jobicy.com/api/v2/remote-jobs"


class JobicyScraper(BaseScraper):
    source = "Jobicy"

    def fetch_jobs(self) -> list[dict]:
        data = self.get_json(API_URL, params={"count": 100})
        jobs = []

        for item in data.get("jobs") or []:
            job = self.build_job(
                title=item.get("jobTitle"),
                company=item.get("companyName"),
                location=item.get("jobGeo"),
                description=(
                    self.clean_html(item.get("jobDescription"))
                    or self.clean_html(item.get("jobExcerpt"))
                    or None
                ),
                url=item.get("url"),
                posted_at=item.get("pubDate"),
            )
            if job:
                jobs.append(job)

        return jobs
