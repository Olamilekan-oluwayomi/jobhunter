"""RemoteOK scraper."""

from scrapers.base import BaseScraper

API_URL = "https://remoteok.com/api"


class RemoteOKScraper(BaseScraper):
    source = "RemoteOK"

    def fetch_jobs(self) -> list[dict]:
        data = self.get_json(API_URL)
        jobs = []

        for item in data[1:]:
            job = self.build_job(
                title=item.get("position"),
                company=item.get("company"),
                location=item.get("location"),
                salary=self._format_salary(item),
                description=self.clean_html(item.get("description")),
                url=item.get("url"),
                posted_at=item.get("epoch") or item.get("date"),
            )
            if job:
                jobs.append(job)

        return jobs

    @staticmethod
    def _format_salary(item: dict) -> str | None:
        minimum = item.get("salary_min") or 0
        maximum = item.get("salary_max") or 0
        if not minimum and not maximum:
            return None
        if minimum and maximum:
            return f"${minimum:,} - ${maximum:,}"
        return f"${minimum or maximum:,}"
