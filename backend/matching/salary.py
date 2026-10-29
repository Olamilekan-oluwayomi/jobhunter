"""Conservative normalization for salary notification thresholds.

Only complete, supported salary expressions are accepted. Bare dollar signs
are treated as USD; explicit foreign currencies and unspecified currencies
are not comparable to the configured USD threshold. No exchange rates are used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_AMOUNT = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_CURRENCY = r"(?:USD\s*\$?|US\$|\$)"
_SALARY = re.compile(
    rf"^\s*(?P<currency>{_CURRENCY})?\s*"
    rf"(?P<low>{_AMOUNT})\s*(?P<low_k>k)?"
    rf"(?:\s*[-\u2013\u2014]\s*(?P<high_currency>{_CURRENCY})?\s*"
    rf"(?P<high>{_AMOUNT})\s*(?P<high_k>k)?)?"
    rf"\s*(?P<suffix_currency>USD)?\s*"
    r"(?:(?:/|per\s+)\s*(?P<period>hours?|hrs?|months?|mos?|years?|yrs?|annum)"
    r"|(?P<label>hourly|monthly|annually|annual|yearly))?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SalaryRange:
    raw: str
    minimum: float
    maximum: float
    period: str
    currency: str = "USD"

    @property
    def annual_minimum(self) -> float:
        # Hourly estimates assume 40 hours/week and 52 weeks/year.
        return self.minimum * {"hour": 40 * 52, "month": 12, "year": 1}[self.period]


def parse_salary(raw: str | None) -> SalaryRange | None:
    """Parse a USD amount/range; return None for ambiguous or unsupported text."""
    match = _SALARY.fullmatch(raw or "")
    if not match:
        return None
    if not any(match[name] for name in ("currency", "high_currency", "suffix_currency")):
        return None
    low = float(match["low"].replace(",", ""))
    high = float((match["high"] or match["low"]).replace(",", ""))
    if match["low_k"]:
        low *= 1000
    if match["high_k"] or (not match["high"] and match["low_k"]):
        high *= 1000
    # A shared suffix such as $100-150k applies to both range bounds.
    if match["high_k"] and not match["low_k"] and low < 1000:
        low *= 1000
    if not 0 < low <= high:
        return None
    unit = (match["period"] or match["label"] or "year").lower()
    period = "hour" if unit.startswith("h") else "month" if unit.startswith("mo") else "year"
    return SalaryRange(raw=raw, minimum=low, maximum=high, period=period)
