"""The weekly poll posting and reminder logic in main.py, driven with fake Discord objects."""

import importlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import discord
import pytest

from models import PollData, RecurringPollConfig, active_polls, active_recurring_configs
from persistence import load_polls, load_recurring_polls, save_poll, save_recurring


@pytest.fixture
def main(monkeypatch):
    """Import main.py without connecting to Discord (it calls bot.run at import time)."""
    monkeypatch.setattr(discord.Client, "run", lambda *_a, **_k: None)
    return importlib.import_module("main")


def _channel(msg_id=777):
    sent = SimpleNamespace(id=msg_id)
    return SimpleNamespace(send=AsyncMock(return_value=sent), fetch_message=AsyncMock())


def _guild(channel, role_members=()):
    role = SimpleNamespace(members=[SimpleNamespace(id=i, bot=False) for i in role_members])
    return SimpleNamespace(get_channel=lambda _cid: channel, get_role=lambda _rid: role)


def _config(**kw):
    base = {
        "event_name": "Weekly", "description": "", "creator_id": 1, "guild_id": 2, "channel_id": 3,
        "post_weekday": 4, "post_hour": 18, "post_minute": 0, "post_timezone": "UTC",
        "expected_respondent_ids": [10, 11], "reminder_days_before": 1,
    }  # fmt: skip
    config = RecurringPollConfig(**{**base, **kw})
    config.id = save_recurring(config)
    return config


async def test_posting_a_recurring_poll_saves_and_tracks_it(main, monkeypatch):
    channel = _channel(777)
    monkeypatch.setattr(main.bot, "get_guild", lambda _gid: _guild(channel))
    config = _config(mention_role_id=55)

    await main._post_recurring_poll(config, "2026-W47")

    channel.send.assert_awaited_once()
    assert channel.send.await_args.kwargs["content"] == "<@&55>"
    assert 777 in active_polls
    assert len(active_polls[777].dates) == 7
    assert active_polls[777].expected_respondent_ids == [10, 11]
    assert [m for m, _ in load_polls()] == [777]
    assert (config.last_posted_week, config.last_poll_msg_id) == ("2026-W47", 777)
    [stored] = load_recurring_polls()
    assert (stored.last_posted_week, stored.last_poll_msg_id) == ("2026-W47", 777)


async def test_posting_closes_the_previous_poll(main, monkeypatch):
    channel = _channel(778)
    old_message = SimpleNamespace(edit=AsyncMock())
    channel.fetch_message = AsyncMock(return_value=old_message)
    monkeypatch.setattr(main.bot, "get_guild", lambda _gid: _guild(channel))
    config = _config(last_poll_msg_id=777)
    old_poll = PollData("Weekly", "", 1, 2, 3, [1])
    active_polls[777] = old_poll
    save_poll(777, old_poll)

    await main._post_recurring_poll(config, "2026-W48")

    assert 777 not in active_polls
    assert [m for m, _ in load_polls()] == [778]
    old_message.edit.assert_awaited_once()
    assert old_message.edit.await_args.kwargs["view"] is None


async def test_posting_does_nothing_when_the_channel_is_gone(main, monkeypatch):
    monkeypatch.setattr(main.bot, "get_guild", lambda _gid: _guild(None))
    config = _config()
    await main._post_recurring_poll(config, "2026-W47")
    assert active_polls == {}
    assert config.last_posted_week is None


def _open_poll(config, **kw):
    poll = PollData(config.event_name, "", 1, 2, 3, [1, 2], expected_respondent_ids=[10, 11], **kw)
    active_polls[777] = poll
    config.last_poll_msg_id = 777
    return poll


# Friday 18:00 UTC is when the poll resets; with 1 reminder day the reminder is due from Thursday 18:00.
THURSDAY_19 = datetime(2026, 11, 26, 19, 0, tzinfo=timezone.utc)
THURSDAY_17 = datetime(2026, 11, 26, 17, 0, tzinfo=timezone.utc)


async def test_reminder_pings_only_people_who_have_not_responded(main, monkeypatch):
    channel = _channel()
    monkeypatch.setattr(main.bot, "get_guild", lambda _gid: _guild(channel))
    config = _config()
    _open_poll(config, votes={0: {10}})

    await main._send_reminders(config, THURSDAY_19)

    channel.send.assert_awaited_once()
    message = channel.send.await_args.args[0]
    assert "<@11>" in message
    assert "<@10>" not in message
    assert config.last_reminded_week == "2026-W48"
    assert load_recurring_polls()[0].last_reminded_week == "2026-W48"


async def test_reminder_is_sent_once_per_cycle(main, monkeypatch):
    channel = _channel()
    monkeypatch.setattr(main.bot, "get_guild", lambda _gid: _guild(channel))
    config = _config()
    _open_poll(config)
    await main._send_reminders(config, THURSDAY_19)
    await main._send_reminders(config, THURSDAY_19 + timedelta(minutes=1))
    assert channel.send.await_count == 1


async def test_no_reminder_before_the_window(main, monkeypatch):
    channel = _channel()
    monkeypatch.setattr(main.bot, "get_guild", lambda _gid: _guild(channel))
    config = _config()
    _open_poll(config)
    await main._send_reminders(config, THURSDAY_17)
    channel.send.assert_not_awaited()
    assert config.last_reminded_week is None


async def test_nobody_pending_marks_the_cycle_without_pinging(main, monkeypatch):
    channel = _channel()
    monkeypatch.setattr(main.bot, "get_guild", lambda _gid: _guild(channel))
    config = _config()
    _open_poll(config, votes={0: {10}, 1: {11}})
    await main._send_reminders(config, THURSDAY_19)
    channel.send.assert_not_awaited()
    assert config.last_reminded_week == "2026-W48"


async def test_role_members_are_resolved_live_at_reminder_time(main, monkeypatch):
    channel = _channel()
    monkeypatch.setattr(main.bot, "get_guild", lambda _gid: _guild(channel, role_members=[30]))
    config = _config(expected_respondent_ids=[], expected_role_id=9)
    _open_poll(config)
    await main._send_reminders(config, THURSDAY_19)
    assert "<@30>" in channel.send.await_args.args[0]


@pytest.mark.parametrize("setup", ["no_open_poll", "nobody_expected", "poll_not_loaded"])
async def test_reminder_skips_when_there_is_nothing_to_remind_about(main, monkeypatch, setup):
    channel = _channel()
    monkeypatch.setattr(main.bot, "get_guild", lambda _gid: _guild(channel))
    config = _config(expected_respondent_ids=[] if setup == "nobody_expected" else [10])
    if setup != "no_open_poll":
        config.last_poll_msg_id = 777
    if setup == "nobody_expected":
        active_polls[777] = PollData("e", "", 1, 2, 3, [1])
    await main._send_reminders(config, THURSDAY_19)
    channel.send.assert_not_awaited()


def _freeze(monkeypatch, main, moment):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment.astimezone(tz) if tz else moment

    monkeypatch.setattr(main, "datetime", FrozenDatetime)


async def test_the_minute_loop_posts_at_the_scheduled_local_time_once_per_week(main, monkeypatch):
    # Friday 18:00 in London (GMT in November) is 18:00 UTC.
    config = _config(post_timezone="Europe/London")
    active_recurring_configs[config.id] = config
    post = AsyncMock()
    monkeypatch.setattr(main, "_post_recurring_poll", post)
    monkeypatch.setattr(main, "_send_reminders", AsyncMock())

    _freeze(monkeypatch, main, datetime(2026, 11, 27, 18, 0, tzinfo=timezone.utc))
    await main.check_recurring_polls.coro()
    post.assert_awaited_once_with(config, "2026-W48")

    config.last_posted_week = "2026-W48"
    await main.check_recurring_polls.coro()
    assert post.await_count == 1  # already posted this week

    post.reset_mock()
    _freeze(monkeypatch, main, datetime(2026, 11, 27, 18, 1, tzinfo=timezone.utc))
    config.last_posted_week = None
    await main.check_recurring_polls.coro()
    post.assert_not_awaited()  # wrong minute


async def test_the_minute_loop_follows_daylight_saving(main, monkeypatch):
    # July: Friday 18:00 in London is 17:00 UTC.
    config = _config(post_timezone="Europe/London")
    active_recurring_configs[config.id] = config
    post = AsyncMock()
    monkeypatch.setattr(main, "_post_recurring_poll", post)
    monkeypatch.setattr(main, "_send_reminders", AsyncMock())
    when = datetime(2026, 7, 10, 17, 0, tzinfo=timezone.utc)
    assert when.astimezone(ZoneInfo("Europe/London")).hour == 18
    _freeze(monkeypatch, main, when)
    await main.check_recurring_polls.coro()
    post.assert_awaited_once()


async def test_one_broken_config_does_not_stop_the_others(main, monkeypatch):
    bad = _config(post_timezone="Not/AZone")
    good = _config()
    active_recurring_configs[bad.id] = bad
    active_recurring_configs[good.id] = good
    post = AsyncMock()
    monkeypatch.setattr(main, "_post_recurring_poll", post)
    monkeypatch.setattr(main, "_send_reminders", AsyncMock())
    _freeze(monkeypatch, main, datetime(2026, 11, 27, 18, 0, tzinfo=timezone.utc))
    await main.check_recurring_polls.coro()
    post.assert_awaited_once_with(good, "2026-W48")
