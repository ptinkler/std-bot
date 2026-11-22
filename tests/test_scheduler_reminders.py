"""Reminding expected respondents who have not answered."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from std_bot.bot import StdBot
from std_bot.domain.poll import PollData
from std_bot.domain.recurring import RecurringPollConfig
from std_bot.scheduler.reminders import send_reminders
from std_bot.storage.recurring import load_recurring, save_recurring
from tests.factories import make_channel, make_draft, make_guild, make_poll, serve_guild

# Friday 18:00 UTC is when the poll resets; with one reminder day the reminder is due from Thursday 18:00.
THURSDAY_19 = datetime(2026, 11, 26, 19, 0, tzinfo=UTC)
THURSDAY_17 = datetime(2026, 11, 26, 17, 0, tzinfo=UTC)


def _setup(
    bot: StdBot, monkeypatch: pytest.MonkeyPatch, *, role_members: tuple[int, ...] = (), **changes: object
) -> tuple[RecurringPollConfig, Any]:
    channel = make_channel()
    serve_guild(bot, monkeypatch, make_guild(channel, role_members))
    return save_recurring(make_draft(**changes)), channel


def _open_poll(bot: StdBot, config: RecurringPollConfig, **changes: object) -> PollData:
    poll = make_poll(event_name=config.event_name, dates=[1, 2], expected_respondent_ids=[10, 11], **changes)
    bot.state.polls[777] = poll
    config.last_poll_msg_id = 777
    return poll


async def test_reminder_pings_only_people_who_have_not_responded(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Respondents are left out, and the cycle is recorded in memory and in the database."""
    config, channel = _setup(bot, monkeypatch)
    _open_poll(bot, config, votes={0: {10}})

    await send_reminders(bot, config, THURSDAY_19)

    channel.send.assert_awaited_once()
    message = channel.send.await_args.args[0]
    assert "<@11>" in message
    assert "<@10>" not in message
    assert config.last_reminded_week == "2026-W48"
    assert load_recurring()[config.id].last_reminded_week == "2026-W48"


async def test_reminder_is_sent_once_per_cycle(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """A second check in the same cycle sends nothing."""
    config, channel = _setup(bot, monkeypatch)
    _open_poll(bot, config)
    await send_reminders(bot, config, THURSDAY_19)
    await send_reminders(bot, config, THURSDAY_19 + timedelta(minutes=1))
    assert channel.send.await_count == 1


async def test_no_reminder_before_the_window(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Before the lead time has started, nothing is sent or recorded."""
    config, channel = _setup(bot, monkeypatch)
    _open_poll(bot, config)
    await send_reminders(bot, config, THURSDAY_17)
    channel.send.assert_not_awaited()
    assert config.last_reminded_week is None


async def test_nobody_pending_marks_the_cycle_without_pinging(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """When everyone has answered, the cycle is still marked so it is not re-checked."""
    config, channel = _setup(bot, monkeypatch)
    _open_poll(bot, config, votes={0: {10}, 1: {11}})
    await send_reminders(bot, config, THURSDAY_19)
    channel.send.assert_not_awaited()
    assert config.last_reminded_week == "2026-W48"


async def test_role_members_are_resolved_live_at_reminder_time(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Members who joined the role after setup are reminded too."""
    config, channel = _setup(bot, monkeypatch, role_members=(30,), expected_respondent_ids=[], expected_role_id=9)
    _open_poll(bot, config)
    await send_reminders(bot, config, THURSDAY_19)
    assert "<@30>" in channel.send.await_args.args[0]


@pytest.mark.parametrize("scenario", ["no_open_poll", "nobody_expected", "poll_not_loaded"])
async def test_reminder_skips_when_there_is_nothing_to_remind_about(
    bot: StdBot, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    """No open poll, no expected respondents, or a poll that is not tracked: nothing is sent."""
    config, channel = _setup(bot, monkeypatch, expected_respondent_ids=[] if scenario == "nobody_expected" else [10])
    if scenario != "no_open_poll":
        config.last_poll_msg_id = 777
    if scenario == "nobody_expected":
        bot.state.polls[777] = make_poll()
    await send_reminders(bot, config, THURSDAY_19)
    channel.send.assert_not_awaited()
