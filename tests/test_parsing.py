"""Parsing of the schedule inputs members type."""

from datetime import time

import pytest

from std_bot.parsing import parse_reminder_days, parse_time, parse_weekday


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", 1), (" 3 ", 3), ("6", 6), ("0", None), ("7", None), ("-1", None), ("x", None), ("", None)],
)
def test_reminder_days_must_be_between_one_and_six(raw: str, expected: int | None) -> None:
    """Zero and a full week or more make no sense as a lead time."""
    assert parse_reminder_days(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("monday", 0),
        ("Monday", 0),
        ("mon", 0),
        ("mo", 0),
        ("0", 0),
        ("tu", 1),
        ("Wednesday", 2),
        ("th", 3),
        ("fri", 4),
        ("sat", 5),
        ("su", 6),
        ("6", 6),
        ("m", None),
        ("s", None),
        ("7", None),
        ("funday", None),
        ("", None),
    ],
)
def test_weekday_accepts_names_prefixes_and_indexes(raw: str, expected: int | None) -> None:
    """A prefix needs two letters, and a bare index must be 0 to 6."""
    assert parse_weekday(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("7pm", time(19, 0)),
        ("7:30 PM", time(19, 30)),
        ("7:30pm", time(19, 30)),
        ("12am", time(0, 0)),
        ("12pm", time(12, 0)),
        ("12:15 AM", time(0, 15)),
        ("19:00", time(19, 0)),
        ("1900", time(19, 0)),
        ("0930", time(9, 30)),
        ("7", time(7, 0)),
        ("23", time(23, 0)),
        ("25:00", None),
        ("12:60", None),
        ("13pm", None),
        ("noon", None),
        ("", None),
        ("930", None),
        ("1900pm", None),
    ],
)
def test_time_accepts_12_and_24_hour_forms(raw: str, expected: time | None) -> None:
    """Only the documented forms parse; everything else is rejected."""
    assert parse_time(raw) == expected
