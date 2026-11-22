"""Listing, editing and cancelling recurring polls."""

import discord
import pytest

from std_bot.bot import StdBot
from std_bot.storage.polls import load_polls
from std_bot.storage.recurring import load_recurring, save_recurring
from std_bot.ui.poll_type import PollTypeView
from std_bot.ui.recurring.edit_view import RecurringEditView
from std_bot.ui.recurring.manage import ManageRecurringView
from tests.factories import make_channel, make_draft, make_guild, make_interaction, make_poll, serve_guild


async def test_manage_lists_only_this_servers_recurring_polls(bot: StdBot) -> None:
    """With none in the server the user is told; otherwise the list view opens."""
    interaction = make_interaction()
    await PollTypeView(bot).manage.callback(interaction)
    assert "No recurring polls" in interaction.response.send_message.await_args.args[0]

    mine = save_recurring(make_draft(guild_id=2))
    other = save_recurring(make_draft(guild_id=99))
    bot.state.recurring.update({mine.id: mine, other.id: other})
    interaction = make_interaction()
    await PollTypeView(bot).manage.callback(interaction)
    view = interaction.response.send_message.await_args.kwargs["view"]
    assert isinstance(view, ManageRecurringView)
    assert list(view.configs) == [mine.id]


async def test_selecting_enables_the_buttons(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Edit and Cancel stay disabled until a poll is picked."""
    config = save_recurring(make_draft())
    view = ManageRecurringView(bot, [config])
    assert view.edit.disabled
    assert view.cancel.disabled
    monkeypatch.setattr(discord.ui.Select, "values", property(lambda _item: [str(config.id)]))

    await view.poll_select.callback(make_interaction())

    assert view.selected == config
    assert not view.edit.disabled
    assert not view.cancel.disabled


async def test_only_the_creator_or_an_admin_can_cancel(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """A stranger is refused; an admin may cancel someone else's poll."""
    config = save_recurring(make_draft(creator_id=1))
    bot.state.recurring[config.id] = config
    view = ManageRecurringView(bot, [config])
    view.selected = config

    stranger = make_interaction(99)
    await view.cancel.callback(stranger)
    assert config.id in load_recurring()
    assert "Only the poll creator" in stranger.response.send_message.await_args.args[0]

    admin = make_interaction(99, manage_guild=True)
    await view.cancel.callback(admin)
    assert load_recurring() == {}
    assert bot.state.recurring == {}


async def test_edit_opens_the_options_view_for_the_creator(bot: StdBot) -> None:
    """The creator gets the edit form; a stranger does not."""
    config = save_recurring(make_draft(creator_id=1))
    view = ManageRecurringView(bot, [config])
    view.selected = config

    stranger = make_interaction(99)
    await view.edit.callback(stranger)
    stranger.response.edit_message.assert_not_awaited()

    creator = make_interaction(1)
    await view.edit.callback(creator)
    assert isinstance(creator.response.edit_message.await_args.kwargs["view"], RecurringEditView)


async def test_saving_edits_updates_the_config_and_the_open_poll(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """The new expected set and option reach the stored config and the poll that is open now."""
    channel = make_channel()
    serve_guild(bot, monkeypatch, make_guild(channel))
    config = save_recurring(make_draft())
    config.last_poll_msg_id = 777
    poll = make_poll(expected_respondent_ids=[10, 11])
    bot.state.polls[777] = poll
    view = RecurringEditView(bot, config)
    view.expected_ids = [20]
    view.allow_cannot_attend = False

    await view.commit_button.callback(make_interaction())

    assert load_recurring()[config.id].expected_respondent_ids == [20]
    assert poll.expected_respondent_ids == [20]
    assert poll.allow_cannot_attend is False
    assert load_polls()[777].expected_respondent_ids == [20]
    channel.fetch_message.assert_awaited_once_with(777)
