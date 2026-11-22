"""Parsing of the free-text schedule inputs members type into forms."""

import re
from datetime import time

from std_bot.domain.schedule import POLL_OPEN_DAYS, WEEKDAY_NAMES

_MERIDIEM = re.compile(r"(?P<body>.*?)\s*(?P<meridiem>AM|PM)")
_CLOCK = re.compile(r"(\d{1,2}):(\d{2})")
_COMPACT = re.compile(r"(\d{2})(\d{2})")
_HOUR_ONLY = re.compile(r"\d{1,2}")
_NOON = 12
_HOURS_IN_DAY = 24
_MINUTES_IN_HOUR = 60
_MIN_PREFIX_LENGTH = 2


def parse_reminder_days(raw: str) -> int | None:
    """Parse the days-before-reset reminder lead time: a whole number from 1 to POLL_OPEN_DAYS - 1.

    Zero is pointless (the poll is resetting right then) and anything at or above
    the open period would land before the poll was even posted.

    Returns:
        The number of days, or None if the input is not valid.
    """
    try:
        days = int(raw.strip())
    except ValueError:
        return None
    return days if 1 <= days < POLL_OPEN_DAYS else None


def parse_weekday(raw: str) -> int | None:
    """Parse a weekday from a name, an unambiguous prefix of two or more letters, or a 0-6 index.

    Returns:
        The weekday with Monday as 0, or None if the input is not a weekday.
    """
    text = raw.strip().lower()
    for index, name in enumerate(WEEKDAY_NAMES):
        lowered = name.lower()
        if text in {lowered, str(index)} or (len(text) >= _MIN_PREFIX_LENGTH and lowered.startswith(text)):
            return index
    return None


def _hour_minute(body: str, *, compact_allowed: bool) -> tuple[int, int] | None:
    """Read "h:mm", "hhmm" (only without AM/PM) or "h" into an hour and a minute."""
    if match := _CLOCK.fullmatch(body):
        return int(match[1]), int(match[2])
    if compact_allowed and (match := _COMPACT.fullmatch(body)):
        return int(match[1]), int(match[2])
    if _HOUR_ONLY.fullmatch(body):
        return int(body), 0
    return None


def _to_24_hour(hour: int, meridiem: str | None) -> int:
    if meridiem == "PM" and hour != _NOON:
        return hour + _NOON
    if meridiem == "AM" and hour == _NOON:
        return 0
    return hour


def parse_time(raw: str) -> time | None:
    """Parse a time of day such as "18:00", "1800", "6pm" or "6:30 PM".

    Returns:
        The time, or None if the input is not a valid time.
    """
    text = raw.strip().upper()
    match = _MERIDIEM.fullmatch(text)
    body = match["body"] if match else text
    meridiem = match["meridiem"] if match else None
    parts = _hour_minute(body, compact_allowed=meridiem is None)
    if parts is None:
        return None
    hour, minute = _to_24_hour(parts[0], meridiem), parts[1]
    if 0 <= hour < _HOURS_IN_DAY and 0 <= minute < _MINUTES_IN_HOUR:
        return time(hour, minute)
    return None
