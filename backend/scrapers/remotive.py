"""Remotive scraper."""

from scrapers.base import BaseScraper

API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveScraper(BaseScraper):
    source = "Remotive"

    def fetch_jobs(self) -> list[dict]:
        data = self.get_json(API_URL)
        jobs = []

        for item in data.get("jobs") or []:
            job = self.build_job(
                title=item.get("title"),
                company=item.get("company_name"),
                location=item.get("candidate_required_location"),
                salary=item.get("salary"),
                description=self.clean_html(item.get("description")),
                url=item.get("url"),
                posted_at=item.get("publication_date"),
            )
            if job:
                jobs.append(job)

        return jobs
