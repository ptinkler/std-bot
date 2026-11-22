"""Weekly schedule arithmetic and date labels."""

import itertools
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from std_bot.domain.schedule import iso_week, next_post_datetime, next_week_dates, upcoming_days
from std_bot.timestamps import date_label, format_date

DAY = 86400
MONDAY_10 = datetime(2026, 11, 23, 10, 0, tzinfo=UTC)


def test_next_post_datetime_is_strictly_after_now() -> None:
    """Exactly now means next week; earlier today wraps; a later weekday stays this week."""
    assert next_post_datetime(0, 10, 0, MONDAY_10) == MONDAY_10 + timedelta(days=7)
    assert next_post_datetime(0, 11, 30, MONDAY_10) == MONDAY_10.replace(hour=11, minute=30)
    assert next_post_datetime(0, 9, 0, MONDAY_10) == MONDAY_10.replace(hour=9) + timedelta(days=7)
    assert next_post_datetime(2, 8, 0, MONDAY_10) == MONDAY_10.replace(hour=8) + timedelta(days=2)
    sunday = datetime(2026, 11, 22, 10, 0, tzinfo=UTC)
    assert next_post_datetime(0, 8, 0, sunday) == sunday.replace(hour=8) + timedelta(days=1)


def test_next_post_datetime_keeps_the_timezone() -> None:
    """The result is in the same zone as the moment it was computed from."""
    now = datetime(2026, 11, 23, 10, 0, tzinfo=ZoneInfo("Europe/London"))
    assert next_post_datetime(4, 18, 0, now).tzinfo == now.tzinfo


def test_next_week_dates_are_next_monday_to_sunday_at_midnight() -> None:
    """Seven consecutive midnights starting on the coming Monday."""
    dates = next_week_dates(datetime(2026, 11, 25, 15, 30, tzinfo=UTC))  # a Wednesday
    assert len(dates) == 7
    assert all(later - earlier == DAY for earlier, later in itertools.pairwise(dates))
    assert datetime.fromtimestamp(dates[0], tz=UTC) == datetime(2026, 11, 30, tzinfo=UTC)


def test_next_week_dates_on_a_monday_start_a_week_later() -> None:
    """On Monday itself, "next week" is the one after this."""
    assert datetime.fromtimestamp(next_week_dates(MONDAY_10)[0], tz=UTC) == datetime(2026, 11, 30, tzinfo=UTC)


def test_upcoming_days_start_tomorrow() -> None:
    """The choices begin with tomorrow's midnight and step by one day."""
    days = upcoming_days(MONDAY_10, 3)
    assert days[0] == int(datetime(2026, 11, 24, tzinfo=UTC).timestamp())
    assert [later - earlier for earlier, later in itertools.pairwise(days)] == [DAY, DAY]


def test_iso_week_uses_the_iso_year() -> None:
    """The first days of January can belong to the previous ISO year."""
    assert iso_week(datetime(2026, 11, 27, tzinfo=UTC)) == "2026-W48"
    assert iso_week(datetime(2027, 1, 1, tzinfo=UTC)) == "2026-W53"


def test_date_formats() -> None:
    """The label has no zero padding; the full form carries Discord's timestamp markup."""
    timestamp = int(datetime(2026, 11, 3, tzinfo=UTC).timestamp())  # a Tuesday
    assert date_label(timestamp) == "Tue, Nov 3"
    assert format_date(timestamp) == f"Tuesday, <t:{timestamp}:D> (<t:{timestamp}:R>)"
