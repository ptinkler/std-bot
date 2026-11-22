from zoneinfo import ZoneInfo

from models import TIMEZONES, PollData


def test_responded_users_unions_votes_and_cannot_attend():
    poll = PollData("e", "", 1, 2, 3, [1, 2], votes={0: {10, 11}, 1: {11, 12}}, cannot_attend={13})
    assert poll.responded_users() == {10, 11, 12, 13}
    assert PollData("e", "", 1, 2, 3, [1]).responded_users() == set()


def test_every_offered_timezone_is_a_valid_iana_key():
    for key, label in TIMEZONES:
        ZoneInfo(key)
        assert label
