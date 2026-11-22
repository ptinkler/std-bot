"""Finalising a poll into a Discord scheduled event."""

from datetime import UTC, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from std_bot.bot import StdBot
from std_bot.storage.polls import load_polls, save_poll
from std_bot.ui.finalize.context import FinalizeContext
from std_bot.ui.finalize.event import finalize_poll
from std_bot.ui.finalize.location import LocationView
from std_bot.ui.finalize.select import FinalizeSelectView
from std_bot.ui.finalize.time_modal import TimeInputModal
from std_bot.ui.finalize.timezone import TimezoneSelectView
from tests.factories import make_channel, make_guild, make_interaction, make_poll

EVENT_TS = 1_800_000_000


def _context(bot: StdBot) -> FinalizeContext:
    poll = make_poll(dates=[int(datetime(2026, 11, 28, tzinfo=UTC).timestamp())])
    bot.state.polls[555] = poll
    save_poll(555, poll)
    return FinalizeContext(bot, poll, 555)


def _interaction_in_guild(channel: object) -> MagicMock:
    interaction = make_interaction()
    interaction.guild = make_guild(channel)
    interaction.guild.create_scheduled_event = AsyncMock(return_value=MagicMock(url="https://discord.test/event"))
    return interaction


async def test_the_date_picker_lists_the_polls_dates(bot: StdBot) -> None:
    """Each date is an option with its vote count."""
    view = FinalizeSelectView(_context(bot))
    assert [option.description for option in view.date.options] == ["0 votes"]


async def test_the_time_modal_rejects_an_unreadable_time(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """A bad time is explained and the flow does not advance."""
    monkeypatch.setattr(discord.ui.TextInput, "value", property(lambda _item: "late"))
    interaction = make_interaction()
    await TimeInputModal(_context(bot), date_index=0).on_submit(interaction)
    assert "Couldn't parse time" in interaction.response.send_message.await_args.args[0]


async def test_the_timezone_step_computes_the_event_timestamp(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """19:00 on the chosen date in New York (EST in November) is 00:00 UTC the next day."""
    monkeypatch.setattr(discord.ui.Select, "values", property(lambda _item: ["America/New_York"]))
    interaction = make_interaction()
    await TimezoneSelectView(_context(bot), 0, time(19, 0)).zone.callback(interaction)
    view = interaction.response.edit_message.await_args.kwargs["view"]
    assert isinstance(view, LocationView)
    assert view.event_ts == int(datetime(2026, 11, 29, 0, 0, tzinfo=UTC).timestamp())


async def test_finalizing_creates_an_external_event_and_closes_the_poll(bot: StdBot) -> None:
    """Without a voice channel the event is external; the poll message is edited and the poll forgotten."""
    channel = make_channel()
    interaction = _interaction_in_guild(channel)

    await finalize_poll(_context(bot), interaction, EVENT_TS, None)

    kwargs = interaction.guild.create_scheduled_event.await_args.kwargs
    assert kwargs["entity_type"] == discord.EntityType.external
    assert kwargs["location"] == "TBD"
    assert kwargs["start_time"] == datetime.fromtimestamp(EVENT_TS, tz=UTC)
    assert kwargs["end_time"] - kwargs["start_time"] == timedelta(hours=2)
    assert bot.state.polls == {}
    assert load_polls() == {}
    channel.fetch_message.return_value.edit.assert_awaited_once()
    interaction.followup.send.assert_awaited_once()


async def test_finalizing_with_a_voice_channel_creates_a_voice_event(bot: StdBot) -> None:
    """The chosen channel is passed on and the event is a voice event."""
    interaction = _interaction_in_guild(make_channel())
    voice = MagicMock(id=44)
    await finalize_poll(_context(bot), interaction, EVENT_TS, voice)
    kwargs = interaction.guild.create_scheduled_event.await_args.kwargs
    assert kwargs["entity_type"] == discord.EntityType.voice
    assert kwargs["channel"] is voice


async def test_a_discord_error_is_reported_and_the_poll_is_kept(bot: StdBot) -> None:
    """If Discord refuses the event, the user is told and nothing is closed."""
    interaction = _interaction_in_guild(make_channel())
    interaction.guild.create_scheduled_event.side_effect = discord.HTTPException(MagicMock(status=400), "nope")
    await finalize_poll(_context(bot), interaction, EVENT_TS, None)
    assert "Failed to create event" in interaction.response.send_message.await_args.args[0]
    assert 555 in bot.state.polls
