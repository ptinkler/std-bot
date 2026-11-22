"""Posting the weekly poll of a recurring config."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from std_bot.bot import StdBot
from std_bot.scheduler.posting import post_recurring_poll
from std_bot.storage.polls import load_polls, save_poll
from std_bot.storage.recurring import load_recurring, save_recurring
from tests.factories import make_channel, make_draft, make_guild, make_poll, serve_guild

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def _serve(bot: StdBot, monkeypatch: pytest.MonkeyPatch, channel: Any) -> None:
    serve_guild(bot, monkeypatch, make_guild(channel))


async def test_posting_a_recurring_poll_saves_and_tracks_it(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """The poll is sent (pinging the role), tracked, stored, and recorded on the config."""
    channel = make_channel(777)
    _serve(bot, monkeypatch, channel)
    config = save_recurring(make_draft(mention_role_id=55))

    await post_recurring_poll(bot, config, "2026-W47", NOW)

    channel.send.assert_awaited_once()
    assert channel.send.await_args.kwargs["content"] == "<@&55>"
    poll = bot.state.polls[777]
    assert len(poll.dates) == 7
    assert poll.expected_respondent_ids == [10, 11]
    assert list(load_polls()) == [777]
    assert (config.last_posted_week, config.last_poll_msg_id) == ("2026-W47", 777)
    stored = load_recurring()[config.id]
    assert (stored.last_posted_week, stored.last_poll_msg_id) == ("2026-W47", 777)


async def test_posting_closes_the_previous_poll(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Last week's poll message is replaced by a closed notice and is no longer tracked."""
    channel = make_channel(778)
    old_message = AsyncMock()
    channel.fetch_message = AsyncMock(return_value=old_message)
    _serve(bot, monkeypatch, channel)
    config = save_recurring(make_draft())
    config.last_poll_msg_id = 777
    old_poll = make_poll()
    bot.state.polls[777] = old_poll
    save_poll(777, old_poll)

    await post_recurring_poll(bot, config, "2026-W48", NOW)

    assert 777 not in bot.state.polls
    assert list(load_polls()) == [778]
    old_message.edit.assert_awaited_once()
    assert old_message.edit.await_args.kwargs["view"] is None


async def test_posting_does_nothing_when_the_channel_is_gone(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """A deleted channel leaves the config untouched."""
    _serve(bot, monkeypatch, None)
    config = save_recurring(make_draft())

    await post_recurring_poll(bot, config, "2026-W47", NOW)

    assert bot.state.polls == {}
    assert config.last_posted_week is None
