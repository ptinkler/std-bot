from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from models import PollData, active_polls
from persistence import load_polls
from ui import PollView

CREATOR = 1


def _interaction(user_id):
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        response=SimpleNamespace(edit_message=AsyncMock(), send_message=AsyncMock(), defer=AsyncMock()),
        message=SimpleNamespace(delete=AsyncMock()),
    )


def _view(**kw):
    poll = PollData("Game night", "", CREATOR, 2, 3, [100, 200, 300], **kw)
    view = PollView(poll)
    view.msg_id = 555
    return view


def _saved(msg_id=555):
    return dict(load_polls())[msg_id]


async def test_buttons_have_unique_custom_ids_and_fit_discords_limits():
    view = _view()
    ids = [item.custom_id for item in view.children]
    assert len(ids) == len(set(ids))
    assert {"vote_0", "vote_1", "vote_2", "cannot_attend", "see_votes", "finalize", "cancel"} == set(ids)
    assert all(len(i) <= 100 for i in ids)
    assert view.timeout is None  # persistent view: survives restarts


async def test_cannot_attend_button_is_optional():
    view = _view(allow_cannot_attend=False)
    assert "cannot_attend" not in [item.custom_id for item in view.children]


async def test_voting_toggles_and_saves():
    view = _view()
    await view._vote_cb(1)(_interaction(10))
    assert view.poll.votes[1] == {10}
    assert _saved().votes[1] == {10}
    await view._vote_cb(1)(_interaction(10))
    assert view.poll.votes[1] == set()
    assert _saved().votes[1] == set()


async def test_voting_for_a_date_clears_cannot_attend():
    view = _view(cannot_attend={10})
    await view._vote_cb(0)(_interaction(10))
    assert 10 not in view.poll.cannot_attend


async def test_cannot_attend_clears_date_votes_and_toggles_off():
    view = _view(votes={0: {10, 11}, 2: {10}})
    await view._cannot_attend_cb(_interaction(10))
    assert view.poll.cannot_attend == {10}
    assert view.poll.votes == {0: {11}, 2: set()}
    assert _saved().cannot_attend == {10}
    await view._cannot_attend_cb(_interaction(10))
    assert view.poll.cannot_attend == set()


async def test_vote_refreshes_the_message():
    view = _view()
    interaction = _interaction(10)
    await view._vote_cb(0)(interaction)
    interaction.response.edit_message.assert_awaited_once()
    assert "**1** person" in interaction.response.edit_message.await_args.kwargs["embed"].description


async def test_see_votes_is_private_and_lists_pending_respondents():
    view = _view(votes={0: {10}}, expected_respondent_ids=[10, 11])
    interaction = _interaction(10)
    await view._see_votes_cb(interaction)
    kwargs = interaction.response.send_message.await_args.kwargs
    assert kwargs["ephemeral"] is True
    pending = next(f for f in kwargs["embed"].fields if "not yet responded" in f.name)
    assert pending.value == "<@11>"


async def test_only_the_creator_can_cancel():
    view = _view()
    active_polls[555] = view.poll
    from persistence import save_poll

    save_poll(555, view.poll)

    stranger = _interaction(99)
    await view._cancel_cb(stranger)
    assert 555 in active_polls
    assert 555 in dict(load_polls())
    stranger.message.delete.assert_not_awaited()

    creator = _interaction(CREATOR)
    await view._cancel_cb(creator)
    assert 555 not in active_polls
    assert 555 not in dict(load_polls())
    creator.message.delete.assert_awaited_once()


@pytest.mark.parametrize("count", [0, 7])
async def test_view_builds_for_any_number_of_dates(count):
    poll = PollData("e", "", 1, 2, 3, list(range(count)))
    assert len(PollView(poll).children) >= 3
