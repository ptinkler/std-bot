"""Creating a one-time poll."""

from datetime import UTC, datetime

import discord
import pytest

from std_bot.bot import StdBot
from std_bot.domain.schedule import upcoming_days
from std_bot.storage.polls import load_polls
from std_bot.ui.one_time import MAX_DATES, DateSelectView
from tests.factories import make_channel, make_interaction

DAYS = upcoming_days(datetime(2026, 11, 22, tzinfo=UTC))


def _pick(monkeypatch: pytest.MonkeyPatch, chosen: list[int]) -> None:
    """Make every select answer with the chosen values, as after a real selection."""
    monkeypatch.setattr(discord.ui.Select, "values", property(lambda _item: [str(day) for day in chosen]))


async def test_confirm_starts_disabled_and_enables_once_dates_are_picked(
    bot: StdBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Confirm button needs at least one date, and the chosen dates are shown in order."""
    view = DateSelectView(bot, "Game night", "", DAYS)
    assert view.confirm.disabled is True
    assert view.dates.max_values == MAX_DATES

    _pick(monkeypatch, [DAYS[1], DAYS[0]])
    interaction = make_interaction()
    await view.dates.callback(interaction)

    assert view.confirm.disabled is False
    assert view.selected == [DAYS[0], DAYS[1]]
    assert "Selected" in interaction.response.edit_message.await_args.kwargs["content"]


async def test_the_toggle_flips_the_cannot_attend_option_and_its_label(bot: StdBot) -> None:
    """The button label shows the state it will leave the poll in."""
    view = DateSelectView(bot, "Game night", "", DAYS)
    assert view.cannot_toggle.label is not None
    assert view.cannot_toggle.label.endswith("ON")
    await view.cannot_toggle.callback(make_interaction())
    assert view.allow_cannot_attend is False
    assert view.cannot_toggle.label.endswith("OFF")


async def test_confirm_posts_and_stores_the_poll(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """The poll is posted in the channel, tracked, and stored under its message id."""
    view = DateSelectView(bot, "Game night", "bring snacks", DAYS)
    view.selected = [DAYS[0], DAYS[1]]
    view.allow_cannot_attend = False
    channel = make_channel(901)
    interaction = make_interaction(42)
    interaction.channel = channel

    await view.confirm.callback(interaction)

    channel.send.assert_awaited_once()
    poll = bot.state.polls[901]
    assert (poll.event_name, poll.description, poll.creator_id) == ("Game night", "bring snacks", 42)
    assert poll.dates == [DAYS[0], DAYS[1]]
    assert poll.allow_cannot_attend is False
    assert load_polls() == {901: poll}
    interaction.response.edit_message.assert_awaited_once()
