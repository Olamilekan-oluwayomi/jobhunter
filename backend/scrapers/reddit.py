"""Reddit job-scraper.

Reddit disabled unauthenticated ``.json`` access (May 2026); anonymous
requests now return HTTP 403 from most IPs. This scraper tries the
public JSON API first and, when that is blocked, falls back to Reddit's
public Atom (RSS) feed, which still serves without credentials. If both
are blocked it reports the source as unavailable instead of hanging or
pretending to work. No authentication, CAPTCHA or access-control bypass
is attempted. Each subreddit is bounded by a short source-specific
timeout and zero retries, and one failing subreddit never blocks the
others.
"""

import time
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from scrapers.base import BaseScraper, ScraperError

SUBREDDITS = ("remotejobs", "forhire", "jobbit")
SUBREDDIT_DELAY = 1.5  # seconds between subreddit requests (respect rate limits)
ATOM_NS = "{http://www.w3.org/2005/Atom}"
USER_AGENT = (
    "JobHunter/1.0 (https://github.com/Olamilekan-oluwayomi/jobhunter; job aggregation bot)"
)
REDDIT_HOSTS = ("reddit.com", "www.reddit.com", "old.reddit.com", "self.reddit")


class RedditScraper(BaseScraper):
    source = "Reddit"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._session.headers["User-Agent"] = USER_AGENT

    def fetch_jobs(self) -> list[dict]:
        self._begin_fetch()
        for index, subreddit in enumerate(SUBREDDITS):
            if index:
                time.sleep(SUBREDDIT_DELAY)
            posts = self._load_subreddit(subreddit)
            jobs = [job for p in posts if (job := self._from_post(p))]
            if jobs:
                self.status = "OK"
                self.status_message = f"fetched via {self._mode}"
                return jobs
        if not self.status_message:
            self.status = "EMPTY"
            self.status_message = "no job posts found in any subreddit"
        return []

    def _load_subreddit(self, subreddit: str) -> list[dict]:
        self._mode = "JSON API"
        try:
            data = self.get_json(
                f"https://www.reddit.com/r/{subreddit}/new.json",
                params={"limit": 100},
            )
            return data.get("data", {}).get("children") or []
        except ScraperError as exc:
            if exc.status_code == 403:
                self.logger.info(
                    "Reddit JSON blocked (HTTP 403) for r/%s; trying RSS feed", subreddit
                )
            else:
                self.logger.warning("Reddit JSON failed for r/%s: %s", subreddit, exc)
            return self._load_rss(subreddit)
        except Exception as exc:
            self.logger.warning("Reddit JSON failed for r/%s: %s", subreddit, exc)
            return self._load_rss(subreddit)

    def _load_rss(self, subreddit: str) -> list[dict]:
        self._mode = "RSS fallback"
        url = f"https://www.reddit.com/r/{subreddit}/new/.rss"
        try:
            text = self.get_text(url)
        except Exception as exc:
            self._fail(subreddit, exc)
            return []
        try:
            return self._parse_rss(text)
        except Exception as exc:
            self._fail(subreddit, exc)
            return []

    def _fail(self, subreddit: str, exc: Exception) -> None:
        code = getattr(exc, "status_code", None)
        if code == 403:
            self.status = "HTTP 403"
            self.status_message = f"r/{subreddit}: HTTP 403 - Reddit blocks anonymous access"
        elif isinstance(code, int):
            self.status = f"HTTP {code}"
            self.status_message = f"r/{subreddit}: HTTP {code} - {exc}"
        elif getattr(exc, "timed_out", False):
            self.status = "TIMEOUT"
            self.status_message = f"r/{subreddit}: request timed out"
        else:
            self.status = "FAILED"
            self.status_message = f"r/{subreddit}: {exc}"
        self.logger.warning("%s", self.status_message)

    @staticmethod
    def _parse_rss(text: str) -> list[dict]:
        """Parse Reddit's Atom feed into the same post shape as the JSON API."""
        root = ET.fromstring(text)
        posts = []
        for entry in root.findall(f"{ATOM_NS}entry"):
            link = entry.find(f"{ATOM_NS}link")
            href = (link.get("href") if link is not None else "") or ""
            posts.append(
                {
                    "data": {
                        "title": (entry.findtext(f"{ATOM_NS}title") or "").strip(),
                        "selftext": entry.findtext(f"{ATOM_NS}content") or "",
                        "permalink": urlparse(href).path if href else "",
                        "created_utc": (
                            entry.findtext(f"{ATOM_NS}published")
                            or entry.findtext(f"{ATOM_NS}updated")
                            or ""
                        ),
                        "domain": urlparse(href).netloc if href else "",
                        "stickied": False,
                        "author": entry.findtext(f"{ATOM_NS}author/{ATOM_NS}name") or "",
                        "url": href,
                    }
                }
            )
        return posts

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

        if self._is_self_domain(domain):
            if permalink.startswith("/"):
                url = f"https://www.reddit.com{permalink}"
            else:
                url = permalink or post.get("url") or ""
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
    def _is_self_domain(domain: str) -> bool:
        d = (domain or "").lower()
        return d in REDDIT_HOSTS or d == "self." or d.endswith(".reddit.com")

    @staticmethod
    def _guess_company(domain: str, post: dict) -> str:
        if domain and not RedditScraper._is_self_domain(domain):
            host = urlparse("https://" + domain).netloc or domain
            return host.lower()
        author = (post.get("author") or "").strip()
        if author and not author.startswith("AutoModerator"):
            return f"u/{author}"
        return "Reddit jobs"
