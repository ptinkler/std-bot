"""Voting rules of a poll, and the timezone list."""

from zoneinfo import ZoneInfo

from std_bot.domain.timezones import TIMEZONES
from tests.factories import make_poll


def test_responded_users_unions_votes_and_cannot_attend() -> None:
    """Anyone who voted or ticked "can't make any" has responded."""
    poll = make_poll(dates=[1, 2], votes={0: {10, 11}, 1: {11, 12}}, cannot_attend={13})
    assert poll.responded_users() == {10, 11, 12, 13}
    assert make_poll().responded_users() == set()


def test_pending_among_keeps_the_order_given() -> None:
    """Only users who have not responded are returned."""
    poll = make_poll(votes={0: {10}}, cannot_attend={11})
    assert poll.pending_among([12, 11, 10, 9]) == [12, 9]


def test_voting_toggles_and_clears_cannot_attend() -> None:
    """A second vote removes the first; voting clears a "can't make any" mark."""
    poll = make_poll(cannot_attend={10})
    assert poll.toggle_vote(0, 10) is True
    assert poll.votes[0] == {10}
    assert poll.cannot_attend == set()
    assert poll.toggle_vote(0, 10) is False
    assert poll.votes[0] == set()


def test_cannot_attend_clears_votes_and_toggles_off() -> None:
    """Ticking "can't make any" removes the user's date votes; ticking again undoes the mark."""
    poll = make_poll(votes={0: {10, 11}, 1: {10}})
    assert poll.toggle_cannot_attend(10) is True
    assert poll.cannot_attend == {10}
    assert poll.votes == {0: {11}, 1: set()}
    assert poll.toggle_cannot_attend(10) is False
    assert poll.cannot_attend == set()


def test_every_offered_timezone_is_a_valid_iana_key() -> None:
    """Each entry has a key `zoneinfo` knows and a label."""
    for key, label in TIMEZONES:
        ZoneInfo(key)
        assert label
