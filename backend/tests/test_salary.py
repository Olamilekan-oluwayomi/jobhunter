"""Salary normalization must not compare incompatible compensation values."""

import pytest

from matching.salary import parse_salary


@pytest.mark.parametrize(
    ("raw", "minimum", "maximum", "period", "annual"),
    [
        ("$100k-$150k", 100_000, 150_000, "year", 100_000),
        ("USD 100-150k", 100_000, 150_000, "year", 100_000),
        ("$100,000 \u2013 $150,000 per year", 100_000, 150_000, "year", 100_000),
        ("100000-150000 USD annually", 100_000, 150_000, "year", 100_000),
        ("US$5,000 per month", 5000, 5000, "month", 60_000),
        ("$5k\u2013$6k/mo", 5000, 6000, "month", 60_000),
        ("$60 / hour", 60, 60, "hour", 124_800),
        ("USD 60-80/hr", 60, 80, "hour", 124_800),
        ("$60.50 hourly", 60.5, 60.5, "hour", 125_840),
        ("$100k", 100_000, 100_000, "year", 100_000),
    ],
)
def test_supported_salary_ranges(raw, minimum, maximum, period, annual):
    salary = parse_salary(raw)
    assert salary is not None
    assert salary.raw == raw
    assert salary.currency == "USD"
    assert salary.minimum == minimum
    assert salary.maximum == maximum
    assert salary.period == period
    assert salary.annual_minimum == annual


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "Competitive",
        "100000",
        "EUR 150000",
        "€150,000",
        "£150,000",
        "NGN 5000000 per month",
        "CAD $150000",
        "A$150000",
        "$150000 CAD",
        "$100k + $20k bonus",
        "Up to $100k",
        "$100k for 20 hours/week",
        "$150k-$100k",
        "$0",
        "$5,00",
        "$60 per day",
        "$100k-$150k EUR",
    ],
)
def test_unsupported_or_ambiguous_salary_is_not_comparable(raw):
    assert parse_salary(raw) is None
