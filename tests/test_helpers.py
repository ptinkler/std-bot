import itertools
from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import helpers
from helpers import (
    build_closed_poll_embed,
    build_poll_embed,
    date_label,
    fmt_date,
    next_post_datetime,
    next_week_dates,
    parse_reminder_days,
    parse_time,
    parse_weekday,
    resolve_expected_ids,
    upcoming_days,
)
from models import PollData

DAY = 86400


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", 1), (" 3 ", 3), ("6", 6), ("0", None), ("7", None), ("-1", None), ("x", None), ("", None), (None, None)],
)
def test_parse_reminder_days(raw, expected):
    assert parse_reminder_days(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("monday", 0), ("Monday", 0), ("mon", 0), ("mo", 0), ("0", 0),
        ("tu", 1), ("Wednesday", 2), ("th", 3), ("fri", 4), ("sat", 5), ("su", 6), ("6", 6),
        ("m", None), ("s", None), ("7", None), ("funday", None), ("", None),
    ],
)  # fmt: skip
def test_parse_weekday(raw, expected):
    assert parse_weekday(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("7pm", time(19, 0)), ("7:30 PM", time(19, 30)), ("7:30pm", time(19, 30)),
        ("12am", time(0, 0)), ("12pm", time(12, 0)), ("12:15 AM", time(0, 15)),
        ("19:00", time(19, 0)), ("1900", time(19, 0)), ("0930", time(9, 30)), ("7", time(7, 0)), ("23", time(23, 0)),
        ("25:00", None), ("12:60", None), ("13pm", None), ("noon", None), ("", None),
    ],
)  # fmt: skip
def test_parse_time(raw, expected):
    assert parse_time(raw) == expected


def test_next_post_datetime_is_strictly_after_now():
    monday_10 = datetime(2026, 11, 23, 10, 0, tzinfo=timezone.utc)  # a Monday
    assert monday_10.weekday() == 0
    # exactly now -> next week, not now
    assert next_post_datetime(0, 10, 0, monday_10) == monday_10 + timedelta(days=7)
    # later today
    assert next_post_datetime(0, 11, 30, monday_10) == monday_10.replace(hour=11, minute=30)
    # earlier today -> next week
    assert next_post_datetime(0, 9, 0, monday_10) == monday_10.replace(hour=9) + timedelta(days=7)
    # a later weekday this week
    assert next_post_datetime(2, 8, 0, monday_10) == monday_10.replace(hour=8) + timedelta(days=2)
    # an earlier weekday wraps to next week
    sunday = datetime(2026, 11, 22, 10, 0, tzinfo=timezone.utc)
    assert next_post_datetime(0, 8, 0, sunday) == sunday.replace(hour=8) + timedelta(days=1)


def test_next_post_datetime_keeps_the_timezone():
    now = datetime(2026, 11, 23, 10, 0, tzinfo=ZoneInfo("Europe/London"))
    assert next_post_datetime(4, 18, 0, now).tzinfo == now.tzinfo


def test_resolve_expected_ids_merges_manual_and_role_members_without_bots():
    role = SimpleNamespace(
        members=[SimpleNamespace(id=5, bot=False), SimpleNamespace(id=6, bot=True), SimpleNamespace(id=2, bot=False)]
    )
    guild = SimpleNamespace(get_role=lambda rid: role if rid == 99 else None)
    assert resolve_expected_ids(guild, 99, [2, 1]) == [1, 2, 5]
    assert resolve_expected_ids(guild, 404, [3]) == [3]  # role no longer exists
    assert resolve_expected_ids(guild, None, [3, 3]) == [3]
    assert resolve_expected_ids(None, 99, [4]) == [4]  # guild gone


def test_next_week_dates_are_next_monday_to_sunday_midnight_utc():
    dates = next_week_dates()
    assert len(dates) == 7
    assert all(b - a == DAY for a, b in itertools.pairwise(dates))
    first = datetime.fromtimestamp(dates[0], tz=timezone.utc)
    assert (first.weekday(), first.hour, first.minute, first.second) == (0, 0, 0, 0)
    assert dates[0] > datetime.now(timezone.utc).timestamp()
    assert dates[0] - datetime.now(timezone.utc).timestamp() <= 7 * DAY


def test_upcoming_days_start_tomorrow():
    days = upcoming_days(3)
    assert len(days) == 3
    assert days[1] - days[0] == DAY
    assert days[0] > datetime.now(timezone.utc).timestamp()


def test_date_formats():
    ts = int(datetime(2026, 11, 3, tzinfo=timezone.utc).timestamp())  # a Tuesday
    assert date_label(ts) == "Tue, Nov 3"  # no zero padding on the day
    assert fmt_date(ts) == f"Tuesday, <t:{ts}:D> (<t:{ts}:R>)"


def _poll(**kw):
    base = {
        "event_name": "Game night", "description": "", "creator_id": 1, "guild_id": 2, "channel_id": 3,
        "dates": [1_000_000, 1_086_400],
    }  # fmt: skip
    return PollData(**{**base, **kw})


def test_poll_embed_counts_votes_and_pluralises():
    poll = _poll(votes={0: {10}, 1: {10, 11}})
    text = build_poll_embed(poll).description
    assert "**1** person\n<@10>" in text
    assert "**2** people" in text


def test_poll_embed_no_votes_yet():
    assert "*no votes yet*" in build_poll_embed(_poll()).description


def test_poll_embed_truncates_long_voter_lists():
    poll = _poll(votes={0: set(range(100, 109))})
    assert "*+3 more…*" in build_poll_embed(poll).description


def test_poll_embed_waiting_on_and_everyone_responded():
    poll = _poll(votes={0: {10}}, cannot_attend={11}, expected_respondent_ids=[10, 11, 12])
    assert "**Waiting on:** <@12>" in build_poll_embed(poll).description
    poll.cannot_attend.add(12)
    assert "Everyone expected has responded" in build_poll_embed(poll).description


def test_poll_embed_cannot_attend_section_and_footer():
    poll = _poll(cannot_attend={7})
    embed = build_poll_embed(poll)
    assert "Can't make any" in embed.description
    assert "🚫" in embed.footer.text
    assert "🚫" not in build_poll_embed(_poll(allow_cannot_attend=False)).footer.text


def test_poll_embed_finalised_and_closed():
    done = build_poll_embed(_poll(description="bring snacks"), finalized_ts=1234)
    assert "<t:1234:F>" in done.description
    assert "bring snacks" in done.description
    assert "Poll Closed" in build_closed_poll_embed(_poll()).title


def test_helpers_module_has_no_import_time_side_effects():
    assert helpers.POLL_OPEN_DAYS == 7
