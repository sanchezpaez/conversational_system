from __future__ import annotations

import re
from datetime import datetime

from app.models import EntityExtraction

# Regex quick legend used below:
# - \b: word boundary (start/end of a word)
# - \s: whitespace (space, tab)
# - \d: digit (0-9)
# - (...): capture group (extract this exact part)
# - (?:...): non-capturing group (group for logic only)
# - ?: optional (0 or 1)
# - *: repeat 0 or more times
# - +: repeat 1 or more times

# Matches order references such as:
# - "order AB-123"
# - "order id: 7821"
# - "order #ZX-9"
# Capturing group 1 returns the order identifier only.
# Pattern breakdown:
# - \border            -> literal word "order"
# - (?:\s+id)?         -> optional " id" after "order"
# - \s*[:#]?\s*        -> optional separators ":" or "#" with optional spaces
# - ([A-Za-z0-9][A-Za-z0-9-]*) -> actual ID (letters/numbers, then letters/numbers/hyphen)
# - \b                 -> stop at word boundary
_ORDER_ID_PATTERN = re.compile(
    r"\border(?:\s+id)?\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9-]*)\b",
    re.IGNORECASE,
)

# Match bare order identifiers such as "AB-123", "ZX-9", or "7821" when the
# user sends only the order reference in the follow-up message.
_BARE_ORDER_ID_PATTERN = re.compile(
    r"\b(?:[A-Za-z]+-\d+|\d+|[A-Za-z0-9]+-\d+[A-Za-z0-9-]*)\b",
    re.IGNORECASE,
)

_DATE_PATTERNS = [
    # ISO-like numeric dates: 2026-04-02 or 2026/04/02
    # Breakdown: year(4 digits) + separator(- or /) + month(2 digits) + separator + day(2 digits)
    re.compile(r"\b\d{4}[-/]\d{2}[-/]\d{2}\b"),
    # Month-first text dates: April 2, 2026 / Apr 2, 2026
    # Breakdown: month name + day number + comma + year
    re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b", re.IGNORECASE),
    # Day-first text dates: 2 April 2026 / 2 Apr 2026
    # Breakdown: day number + month name + year
    re.compile(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4}\b", re.IGNORECASE),
]

# Parsing formats used to normalize any supported date expression
# into ISO format (YYYY-MM-DD).
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
)

_PREVIOUS_ORDER_REFERENCE_PATTERNS = [
    re.compile(r"\bthat\s+order\b", re.IGNORECASE),
    re.compile(r"\bsame\s+order\b", re.IGNORECASE),
    re.compile(r"\bthat\s+booking\b", re.IGNORECASE),
]

_PREVIOUS_DATE_REFERENCE_PATTERNS = [
    re.compile(r"\bthe\s+same\s+date\b", re.IGNORECASE),
    re.compile(r"\bsame\s+date\b", re.IGNORECASE),
    re.compile(r"\bthat\s+date\b", re.IGNORECASE),
]


def extract_entities_locally(message: str) -> EntityExtraction:
    """Extract order_id and date from raw user text using local regex rules.

    Examples:
    - "Where is my order AB-123?" -> order_id="AB-123", date=None
    - "Move order 7821 to 2026/04/02" -> order_id="7821", date="2026-04-02"
    - "Please change order ZX-9 to April 2, 2026" -> order_id="ZX-9", date="2026-04-02"

    Returns an EntityExtraction with any missing field set to None.
    """
    order_id = _extract_order_id(message)
    date = _extract_date(message)
    return EntityExtraction(order_id=order_id, date=date)



def _extract_order_id(message: str) -> str | None:
    """Return the first matched order identifier, if present."""
    match = _ORDER_ID_PATTERN.search(message)
    if match:
        return match.group(1)

    for candidate in _BARE_ORDER_ID_PATTERN.findall(message):
        cleaned = candidate.strip()
        if any(token in cleaned.lower() for token in ("where", "move", "change", "order", "booking", "date")):
            continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
            continue
        return cleaned

    return None



def _extract_date(message: str) -> str | None:
    """Return the first valid date found, normalized to YYYY-MM-DD."""
    for pattern in _DATE_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue

        normalized = _normalize_date(match.group(0))
        if normalized:
            return normalized

    return None



def _normalize_date(raw_date: str) -> str | None:
    """Normalize a date string to ISO format, or None if parsing fails."""
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(raw_date, date_format).date().isoformat()
        except ValueError:
            continue

    return None


def references_previous_order(message: str) -> bool:
    """Return True when text refers to a previously mentioned order."""
    return any(pattern.search(message) for pattern in _PREVIOUS_ORDER_REFERENCE_PATTERNS)


def references_previous_date(message: str) -> bool:
    """Return True when text refers to a previously mentioned date."""
    return any(pattern.search(message) for pattern in _PREVIOUS_DATE_REFERENCE_PATTERNS)
