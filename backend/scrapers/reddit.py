"""Reddit job-scraper.

Primary source is the Reddit JSON API; falls back to the PullPush
archive API when Reddit blocks the request. Reddit listings have no
reliable company/location/salary fields, so those are derived from
the post URL/per-domain and left blank when unknown.
"""

from urllib.parse import urlparse

from scrapers.base import BaseScraper

SUBREDDITS = ("remotejobs", "forhire", "jobbit")
PULLPUSH_URL = "https://api.pullpush.io/reddit/search/submission/"


class RedditScraper(BaseScraper):
    source = "Reddit"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._session.headers["User-Agent"] = "JobHunter/1.0 (job aggregation bot)"

    def fetch_jobs(self) -> list[dict]:
        for subreddit in SUBREDDITS:
            try:
                posts = self._load_subreddit(subreddit)
            except Exception as exc:
                self.logger.warning("could not load r/%s: %s", subreddit, exc)
                continue
            jobs = [job for p in posts if (job := self._from_post(p))]
            if jobs:
                return jobs
        return []

    def _load_subreddit(self, subreddit: str) -> list[dict]:
        try:
            data = self.get_json(
                f"https://www.reddit.com/r/{subreddit}/new.json",
                params={"limit": 100},
            )
            return data["data"]["children"]
        except Exception:
            data = self.get_json(
                PULLPUSH_URL,
                params={"subreddit": subreddit, "size": 25},
            )
            return [{"data": child, "kind": "t3"} for child in data.get("data") or []]

    def _from_post(self, raw: dict) -> dict | None:
        post = raw.get("data") or {}
        title = post.get("title") or ""
        text = post.get("selftext") or ""
        permalink = post.get("permalink") or ""
        created = post.get("created_utc")
        domain = post.get("domain") or ""

        if post.get("stickied"):
            return None
        if len(title) < 3:
            return None

        if domain in ("self.", "") or domain == "self.reddit":
            url = f"https://www.reddit.com{permalink}"
        else:
            url = post.get("url") or f"https://www.reddit.com{permalink}"

        company = self._guess_company(domain, post)
        description = self.clean_html(text)
        location = "Remote"

        return self.build_job(
            title=title,
            company=company,
            location=location,
            description=description,
            url=url,
            posted_at=created,
        )

    @staticmethod
    def _guess_company(domain: str, post: dict) -> str:
        if domain and domain not in ("self.reddit", "reddit.com"):
            host = urlparse("https://" + domain).netloc or domain
            return host.lower()
        author = (post.get("author") or "").strip()
        if author and not author.startswith("AutoModerator"):
            return f"u/{author}"
        return "Reddit jobs"
