"""Public board normalization and isolation, with no network or database."""

from unittest.mock import Mock

import pytest

from scrapers.base import ScraperError
from scrapers.company_boards import AshbyScraper, LeverScraper
from scrapers.manager import build_scrapers


def lever_post(**overrides):
    return {
        "text": "Frontend Engineer",
        "hostedUrl": "https://jobs.lever.co/acme/job-one",
        "categories": {"location": "United States", "commitment": "Full-time"},
        "workplaceType": "remote",
        "descriptionPlain": "Build React interfaces.",
        "lists": [{"text": "Requirements", "content": "<li>TypeScript &amp; CSS</li>"}],
        "salaryRange": {"currency": "USD", "interval": "year", "min": 60000, "max": 90000},
        **overrides,
    }


def ashby_post(**overrides):
    return {
        "title": "Product Engineer",
        "jobUrl": "https://jobs.ashbyhq.com/acme/job-one",
        "location": "Lagos",
        "isListed": True,
        "isRemote": True,
        "workplaceType": "Hybrid",
        "descriptionHtml": "<p>React &amp; Python</p>",
        "publishedAt": "2026-10-20T12:00:00Z",
        "compensation": {"scrapeableCompensationSalarySummary": "USD 60000-80000"},
        **overrides,
    }


def test_boards_disabled_without_configuration(monkeypatch):
    monkeypatch.delenv("LEVER_BOARDS", raising=False)
    monkeypatch.delenv("ASHBY_BOARDS", raising=False)
    from config import reload_settings

    reload_settings()
    scrapers, disabled = build_scrapers("Lever,Ashby")
    assert scrapers == []
    assert set(disabled) == {"Lever", "Ashby"}


def test_lever_preserves_location_requirements_and_salary():
    scraper = LeverScraper()
    scraper.board_entries = lambda: ["acme|Acme Inc"]
    scraper.get_json = Mock(return_value=[lever_post()])
    job = scraper.fetch_jobs()[0]
    assert job["company"] == "Acme Inc"
    assert job["source"] == "Lever"
    assert job["location"] == "remote · United States"
    assert job["salary"] == "USD 60000-90000 / year"
    assert "TypeScript & CSS" in job["description"]
    assert job["posted_at"] is None


def test_lever_fetches_next_page(monkeypatch):
    monkeypatch.setattr("scrapers.company_boards.LEVER_PAGE_SIZE", 1)
    scraper = LeverScraper()
    scraper.board_entries = lambda: ["acme"]
    scraper.get_json = Mock(side_effect=[[lever_post()], []])
    assert len(scraper.fetch_jobs()) == 1
    assert scraper.get_json.call_args.kwargs["params"]["skip"] == 1


def test_lever_reports_page_cap_instead_of_silent_truncation(monkeypatch):
    monkeypatch.setattr("scrapers.company_boards.LEVER_PAGE_SIZE", 1)
    monkeypatch.setattr("scrapers.company_boards.LEVER_MAX_PAGES", 1)
    scraper = LeverScraper()
    scraper.board_entries = lambda: ["acme"]
    scraper.get_json = Mock(return_value=[lever_post()])
    assert scraper.fetch_jobs() == []
    assert scraper.status == "FAILED"
    assert "page fetch limit" in scraper.status_message


def test_failed_board_does_not_hide_successful_board():
    scraper = LeverScraper()
    scraper.board_entries = lambda: ["missing", "acme|Acme"]
    scraper.get_json = Mock(side_effect=[ScraperError("HTTP 404"), [lever_post()]])
    assert len(scraper.fetch_jobs()) == 1
    assert scraper.status == "PARTIAL"
    assert "missing" in scraper.status_message


@pytest.mark.parametrize("entry", ["../private", "https://example.com", "acme|", "a/b"])
def test_invalid_board_config_never_makes_request(entry):
    scraper = LeverScraper()
    scraper.board_entries = lambda: [entry]
    scraper.get_json = Mock()
    assert scraper.fetch_jobs() == []
    scraper.get_json.assert_not_called()
    assert scraper.status == "FAILED"


def test_ashby_excludes_unlisted_and_does_not_label_hybrid_as_remote():
    scraper = AshbyScraper()
    scraper.board_entries = lambda: ["acme|Acme"]
    scraper.get_json = Mock(
        return_value={
            "jobs": [
                ashby_post(),
                ashby_post(isListed=False),
                ashby_post(isListed=None),
            ]
        }
    )
    jobs = scraper.fetch_jobs()
    assert len(jobs) == 1
    assert jobs[0]["location"] == "Hybrid · Lagos"
    assert jobs[0]["description"] == "React & Python"
    assert jobs[0]["salary"] == "USD 60000-80000"
    assert jobs[0]["posted_at"].year == 2026


@pytest.mark.parametrize("payload", [None, {}, {"jobs": "bad"}, {"jobs": [None]}])
def test_ashby_malformed_payload_is_visible_failure(payload):
    scraper = AshbyScraper()
    scraper.board_entries = lambda: ["acme"]
    scraper.get_json = Mock(return_value=payload)
    assert scraper.fetch_jobs() == []
    assert scraper.status == "FAILED"
