"""Persistence of open polls."""

import json

from std_bot.database.engine import open_session
from std_bot.database.tables import PollRow
from std_bot.domain.poll import PollData
from std_bot.storage.polls import delete_poll, load_polls, save_poll
from tests.factories import make_poll


def _poll() -> PollData:
    return make_poll(
        description="bring snacks",
        votes={0: {10, 11}, 1: set()},
        cannot_attend={12},
        allow_cannot_attend=False,
        expected_respondent_ids=[10, 11, 12],
    )


def test_poll_round_trip_keeps_everything() -> None:
    """What is saved is what is loaded, with votes as sets again."""
    save_poll(555, _poll())
    assert load_polls() == {555: _poll()}


def test_saving_a_poll_twice_updates_in_place() -> None:
    """The second save replaces the first instead of adding a row."""
    poll = _poll()
    save_poll(555, poll)
    poll.votes[1].add(99)
    save_poll(555, poll)
    assert load_polls()[555].votes[1] == {99}


def test_delete_poll_and_deleting_a_missing_one() -> None:
    """Deleting twice is harmless."""
    save_poll(1, _poll())
    delete_poll(1)
    delete_poll(1)
    assert load_polls() == {}


def test_old_poll_rows_without_newer_fields_load_with_defaults() -> None:
    """Rows written before "can't make any" and expected respondents existed still load."""
    legacy = {
        "event_name": "Old",
        "description": "",
        "creator_id": 1,
        "guild_id": 2,
        "channel_id": 3,
        "dates": [1],
        "votes": {"0": [5]},
    }
    with open_session() as session:
        session.add(PollRow(msg_id=9, data=json.dumps(legacy)))
        session.commit()
    poll = load_polls()[9]
    assert poll.cannot_attend == set()
    assert poll.allow_cannot_attend is True
    assert poll.expected_respondent_ids == []
