"""The buttons under a poll message."""

import discord
import pytest

from std_bot.bot import StdBot
from std_bot.storage.polls import load_polls, save_poll
from std_bot.ui.poll_view import PollView
from tests.factories import make_interaction, make_poll

CREATOR = 1


def _view(bot: StdBot, **changes: object) -> PollView:
    poll = make_poll(dates=[100, 200, 300], creator_id=CREATOR, **changes)
    save_poll(555, poll)
    return PollView(bot, poll)


def _custom_ids(view: PollView) -> list[str]:
    return [str(item.custom_id) for item in view.children if isinstance(item, discord.ui.Button)]


async def test_buttons_have_unique_custom_ids_and_fit_discords_limits(bot: StdBot) -> None:
    """Persistent views need stable, unique ids of at most 100 characters."""
    view = _view(bot)
    ids = _custom_ids(view)
    assert len(ids) == len(set(ids))
    assert set(ids) == {"vote_0", "vote_1", "vote_2", "cannot_attend", "see_votes", "finalize", "cancel"}
    assert all(len(custom_id) <= 100 for custom_id in ids)
    assert view.timeout is None


async def test_cannot_attend_button_is_optional(bot: StdBot) -> None:
    """Polls created without the option have no such button."""
    assert "cannot_attend" not in _custom_ids(_view(bot, allow_cannot_attend=False))


@pytest.mark.parametrize("count", [0, 7])
async def test_view_builds_for_any_number_of_dates(bot: StdBot, count: int) -> None:
    """A poll with no dates or a full week both get a view."""
    view = PollView(bot, make_poll(dates=list(range(count))))
    assert len(view.children) >= count + 3


async def test_voting_toggles_and_saves(bot: StdBot) -> None:
    """The first press adds the vote, the second removes it, and both are stored."""
    view = _view(bot)
    await view.vote(make_interaction(10), 1)
    assert load_polls()[555].votes[1] == {10}
    await view.vote(make_interaction(10), 1)
    assert load_polls()[555].votes[1] == set()


async def test_vote_refreshes_the_message(bot: StdBot) -> None:
    """The poll message is edited with the new counts."""
    view = _view(bot)
    interaction = make_interaction(10)
    await view.vote(interaction, 0)
    interaction.response.edit_message.assert_awaited_once()
    assert "**1** person" in interaction.response.edit_message.await_args.kwargs["embed"].description


async def test_cannot_attend_button_toggles_and_saves(bot: StdBot) -> None:
    """The button marks the user (clearing their votes) and a second press unmarks them."""
    view = _view(bot, votes={0: {10, 11}, 2: {10}})
    await view.cannot_attend.callback(make_interaction(10))
    assert load_polls()[555].cannot_attend == {10}
    assert load_polls()[555].votes == {0: {11}, 2: set()}
    await view.cannot_attend.callback(make_interaction(10))
    assert load_polls()[555].cannot_attend == set()


async def test_see_votes_is_private_and_lists_pending_respondents(bot: StdBot) -> None:
    """The votes embed is ephemeral and names who is still expected."""
    view = _view(bot, votes={0: {10}}, expected_respondent_ids=[10, 11])
    interaction = make_interaction(10)
    await view.see_votes.callback(interaction)
    kwargs = interaction.response.send_message.await_args.kwargs
    assert kwargs["ephemeral"] is True
    pending = next(field for field in kwargs["embed"].fields if "not yet responded" in field.name)
    assert pending.value == "<@11>"


async def test_finalize_offers_the_dates_with_vote_counts(bot: StdBot) -> None:
    """The reply lists every date and carries the date picker."""
    view = _view(bot, votes={0: {10}})
    interaction = make_interaction(CREATOR)
    await view.finalize.callback(interaction)
    args, kwargs = interaction.response.send_message.await_args
    assert "**1.**" in args[0]
    assert "1 votes" in args[0]
    assert kwargs["ephemeral"] is True


async def test_only_the_creator_can_cancel(bot: StdBot) -> None:
    """A stranger is refused; the creator removes the poll everywhere and deletes the message."""
    view = _view(bot)
    bot.state.polls[555] = view.poll

    stranger = make_interaction(99)
    await view.cancel.callback(stranger)
    assert 555 in bot.state.polls
    assert 555 in load_polls()
    stranger.message.delete.assert_not_awaited()

    creator = make_interaction(CREATOR)
    await view.cancel.callback(creator)
    assert 555 not in bot.state.polls
    assert 555 not in load_polls()
    creator.message.delete.assert_awaited_once()
