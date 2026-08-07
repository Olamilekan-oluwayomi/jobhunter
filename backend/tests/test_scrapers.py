"""Hermetic tests for the scraping pipeline.

No network and no database: scraper outcomes are exercised with stub
classes and injected payloads so the suite stays fast and deterministic.
"""

from __future__ import annotations

from scrapers.base import BaseScraper, ScraperError
from scrapers.manager import ScraperManager
from scrapers.reddit import RedditScraper


class _StubScraper(BaseScraper):
    source = "Stub"

    def __init__(self, *, payload: list | None = None, boom: Exception | None = None) -> None:
        super().__init__()
        self._payload = payload or []
        self._boom = boom

    def fetch_jobs(self) -> list[dict]:
        if self._boom is not None:
            raise self._boom
        return list(self._payload)


class _BoomScraper:
    source = "Boom"

    def _begin_fetch(self) -> None:
        self.status = "OK"
        self.status_message = ""

    def fetch_jobs(self) -> list[dict]:
        raise RuntimeError("simulated crash")


class _TimeoutScraper:
    source = "Timeout"

    def _begin_fetch(self) -> None:
        self.status = "OK"
        self.status_message = ""

    def fetch_jobs(self) -> list[dict]:
        raise ScraperError("GET x timed out", timed_out=True)


class _MalformedScraper:
    source = "Malformed"

    def _begin_fetch(self) -> None:
        self.status = "OK"
        self.status_message = ""

    def fetch_jobs(self) -> list[dict]:
        raise ScraperError("GET x returned invalid JSON")


def _job(title: str, url: str) -> dict:
    return {
        "title": title,
        "company": "Acme",
        "location": "Remote",
        "salary": None,
        "description": None,
        "url": url,
        "source": "Stub",
        "posted_at": None,
    }


def test_build_job_counts_raw_and_normalizes() -> None:
    scraper = _StubScraper()
    scraper._begin_fetch()
    job = scraper.build_job(
        title="Python Dev",
        company="Acme",
        url="https://acme.example/jobs/1",
        location="Remote",
    )
    assert job is not None
    assert job["source"] == "Stub"
    # A valid item plus a short-title reject both count as raw items.
    assert scraper.build_job(title="ab", company="Acme", url="https://acme.example/jobs/2") is None
    assert scraper.raw_count == 2
    assert scraper.status == "OK"


def test_manager_isolates_failures() -> None:
    good = _StubScraper(payload=[_job("Good Job", "https://good.example/1")])
    manager = ScraperManager(
        scrapers=[good, _BoomScraper(), _TimeoutScraper(), _MalformedScraper()],
        disabled_sources=["Reddit"],
    )
    fetched = manager.fetch_all()

    assert [j["url"] for j in fetched] == ["https://good.example/1"]
    assert manager.results["Stub"].status == "OK"
    assert manager.results["Stub"].parsed == 1
    assert manager.results["Boom"].status == "FAILED"
    assert manager.results["Timeout"].status == "TIMEOUT"
    assert manager.results["Malformed"].status == "FAILED"
    assert manager.results["Reddit"].status == "DISABLED"


def test_manager_dedupes_by_url() -> None:
    shared = _job("Shared", "https://dup.example/1")
    a = _StubScraper(payload=[shared])
    b = _StubScraper(
        payload=[_job("Other", "https://dup.example/1"), _job("Unique", "https://dup.example/2")]
    )
    manager = ScraperManager(scrapers=[a, b])
    fetched = manager.fetch_all()
    assert len(fetched) == 2
    assert {j["url"] for j in fetched} == {"https://dup.example/1", "https://dup.example/2"}


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <author><name>hiring-company</name></author>
    <title>[HIRING] Senior Backend Engineer</title>
    <link href="https://www.reddit.com/r/remotejobs/comments/abc1/senior_backend/" />
    <published>2026-01-05T10:00:00+00:00</published>
    <content type="html">We need &lt;b&gt;Python&lt;/b&gt; skills. Apply now!</content>
  </entry>
</feed>
"""


def test_reddit_parses_rss_into_posts() -> None:
    posts = RedditScraper._parse_rss(SAMPLE_RSS)
    assert len(posts) == 1
    data = posts[0]["data"]
    assert data["title"] == "[HIRING] Senior Backend Engineer"
    assert data["author"] == "hiring-company"
    assert data["permalink"] == "/r/remotejobs/comments/abc1/senior_backend/"
    assert data["url"] == "https://www.reddit.com/r/remotejobs/comments/abc1/senior_backend/"


def test_reddit_rss_post_builds_job(monkeypatch) -> None:
    scraper = RedditScraper(timeout=5, max_retries=0)
    scraper._begin_fetch()
    posts = RedditScraper._parse_rss(SAMPLE_RSS)
    job = scraper._from_post(posts[0])
    assert job is not None
    assert job["title"] == "[HIRING] Senior Backend Engineer"
    assert job["company"] == "u/hiring-company"
    assert job["url"] == "https://www.reddit.com/r/remotejobs/comments/abc1/senior_backend/"
    assert job["posted_at"] is not None


def test_upwork_without_token_is_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("UPWORK_TOKEN", raising=False)
    from scrapers.upwork import UpworkScraper

    scraper = UpworkScraper()
    scraper._begin_fetch()
    assert scraper.fetch_jobs() == []
    assert scraper.status == "UNAVAILABLE"
    assert "UPWORK_TOKEN" in scraper.status_message


def test_upwork_malformed_response_is_failed(monkeypatch) -> None:
    monkeypatch.setenv("UPWORK_TOKEN", "not-a-real-token")
    from scrapers.upwork import UpworkScraper

    scraper = UpworkScraper()

    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "text/html"}

        def json(self):
            raise ValueError("bad payload")

    scraper.get = lambda *a, **k: FakeResponse()  # type: ignore[method-assign]
    scraper._begin_fetch()
    assert scraper.fetch_jobs() == []
    assert scraper.status == "FAILED"
    assert "non-JSON" in scraper.status_message
